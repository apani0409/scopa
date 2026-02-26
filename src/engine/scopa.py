"""
src/engine/scopa.py
===================
Complete Scopa game engine — pure Python, standard library only.

Design principles
-----------------
* **Immutable state** — every public method consumes a ``GameState`` and returns
  a *new* ``GameState``; the original is never mutated.
* **Deterministic** — given the same shuffled deck the game always plays out
  identically; randomness is isolated to :py:meth:`ScopaEngine.create_game`.
* **Server-authoritative** — the engine validates every action and raises a
  typed exception before any state change is applied.
* **Deck-agnostic** — the only suit that carries special game meaning is ``"oro"``
  (coins); everything else is configurable via :class:`GameConfig`.
* **Test-friendly** — small private helpers are the unit-test surface; public
  methods compose them.

Exception hierarchy (new game-play exceptions, extends existing engine ones)
-----------------------------------------------------------------------------
``ScopaEngineError``
├── ``WrongTurnError``             — action from the wrong player
├── ``CardNotInHandError``         — played card is not in the player's hand
├── ``InvalidCaptureError``        — proposed capture set is illegal
└── ``EqualValuePriorityError``    — player must capture the equal-value card
                                     instead of a sum combination
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from itertools import combinations
from typing import Optional

from .exceptions import ScopaEngineError
from .models import Card


# ════════════════════════════════════════════════════════════════════════════
#  Game-play exceptions
# ════════════════════════════════════════════════════════════════════════════

class WrongTurnError(ScopaEngineError):
    """Raised when a player attempts to act outside their turn."""

    def __init__(self, acting: str, expected: str) -> None:
        super().__init__(
            f"It is '{expected}'s turn, not '{acting}'s."
        )
        self.acting = acting
        self.expected = expected


class CardNotInHandError(ScopaEngineError):
    """Raised when the played card is not in the acting player's hand."""

    def __init__(self, card_id: str, player_id: str) -> None:
        super().__init__(
            f"Card '{card_id}' is not in '{player_id}'s hand."
        )
        self.card_id = card_id
        self.player_id = player_id


class InvalidCaptureError(ScopaEngineError):
    """
    Raised when the proposed set of table-card IDs does not constitute a
    legal capture for the played card.
    """

    def __init__(self, reason: str, card_id: str, capture_ids: list[str]) -> None:
        super().__init__(
            f"Invalid capture for card '{card_id}' "
            f"(targets: {capture_ids}): {reason}"
        )
        self.card_id = card_id
        self.capture_ids = capture_ids


class EqualValuePriorityError(ScopaEngineError):
    """
    Raised when the player proposes a sum-combination capture but an
    exact-value match exists on the table — the exact match must be taken.
    """

    def __init__(self, card_id: str, matching_id: str) -> None:
        super().__init__(
            f"Card '{card_id}' must capture the equal-value table card "
            f"'{matching_id}' (exact match takes priority over sums)."
        )
        self.card_id = card_id
        self.matching_id = matching_id


# ════════════════════════════════════════════════════════════════════════════
#  Game configuration
# ════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GameConfig:
    """
    Engine-level knobs.

    Changing these is the only thing needed to support rule variants or
    future deck sizes without touching engine logic.

    Attributes
    ----------
    hand_size:
        Cards dealt to each player per deal (standard: 3).
    initial_table_size:
        Cards placed on the table at game start (standard: 4).
    coins_suit:
        The suit name that carries "coins" semantics (settebello, primiera
        coins count).  Use ``"oro"`` for Neapolitan decks.
    """

    hand_size: int = 3
    initial_table_size: int = 4
    coins_suit: str = "oro"

    # Primiera point values (standard Italian Scopa rules)
    primiera_values: dict[int, int] = field(default_factory=lambda: {
        7: 21,
        6: 18,
        1: 16,
        5: 15,
        4: 14,
        3: 13,
        2: 12,
    })

    def primiera_score(self, value: int) -> int:
        """Return the primiera point value for a card rank."""
        return self.primiera_values.get(value, 10)


# ════════════════════════════════════════════════════════════════════════════
#  State dataclasses
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class PlayerState:
    """
    Mutable snapshot of a single player's state within one round.

    Attributes
    ----------
    id:
        Unique player identifier (opaque string; engine never parses it).
    hand:
        Cards currently held by the player, not yet played.
    captured:
        All cards this player has captured so far this round (including
        the played card itself).
    scopas:
        Number of scopa events scored by this player this round.
    """

    id: str
    hand: list[Card]
    captured: list[Card]
    scopas: int = 0


@dataclass
class GameState:
    """
    Complete, serialisable snapshot of the game at any point in time.

    The engine never stores state internally — it only reads ``GameState``
    in and returns a new ``GameState`` out.

    Attributes
    ----------
    deck:
        Cards remaining in the draw pile (top = index 0).
    table:
        Cards currently face-up on the table.
    players:
        Ordered list of :class:`PlayerState`.  Index 0 goes first.
    current_player_index:
        Index into ``players`` of whoever acts next.
    last_capture_player_id:
        ``id`` of the player who last made a capture this round, or
        ``None`` if no capture has been made yet.  Used at round-end to
        award remaining table cards.
    scores:
        Cumulative *round* scores keyed by player id.  Reset to ``{}``
        at the start of each new round; the caller is responsible for
        accumulating across rounds.
    phase:
        Life-cycle marker: ``"playing"`` → ``"scoring"`` → ``"finished"``.
    config:
        Engine configuration snapshot baked into this state.
    """

    deck: list[Card]
    table: list[Card]
    players: list[PlayerState]
    current_player_index: int
    last_capture_player_id: Optional[str]
    scores: dict[str, int]
    phase: str  # "playing" | "scoring" | "finished"
    config: GameConfig = field(default_factory=GameConfig)

    # ── Derived helpers (read-only, never used in game logic) ─────────────────

    @property
    def current_player(self) -> PlayerState:
        """The player whose turn it currently is."""
        return self.players[self.current_player_index]

    def player_by_id(self, player_id: str) -> PlayerState:
        """Return the :class:`PlayerState` for *player_id*."""
        for p in self.players:
            if p.id == player_id:
                return p
        raise KeyError(f"No player with id '{player_id}'.")


# ════════════════════════════════════════════════════════════════════════════
#  Engine
# ════════════════════════════════════════════════════════════════════════════

class ScopaEngine:
    """
    Stateless Scopa game engine.

    All public methods accept a :class:`GameState`, validate the requested
    action, and return a *new* :class:`GameState`.  They never mutate their
    inputs.

    Typical game loop
    -----------------
    ::

        engine = ScopaEngine()
        state  = engine.create_game(cards, ["alice", "bob"])

        while not engine.is_round_over(state):
            state = engine.deal_if_needed(state)

            # Obtain action from player / AI / network …
            state = engine.play_card(state, player_id, card_id, capture_ids)

        state = engine.calculate_round_score(state)
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def create_game(
        self,
        deck: list[Card],
        player_ids: list[str],
        config: Optional[GameConfig] = None,
        *,
        seed: Optional[int] = None,
    ) -> GameState:
        """
        Initialise a brand-new round from a loaded deck.

        The deck is shuffled in place on a *copy* (the caller's list is
        untouched).  Pass *seed* for deterministic tests.

        Parameters
        ----------
        deck:
            All 40 :class:`~src.engine.models.Card` objects from
            :func:`~src.engine.loader.loadDeck`.
        player_ids:
            Ordered list of player identifiers.  Currently only two-player
            games are supported; exactly two IDs must be provided.
        config:
            Optional :class:`GameConfig` override.  ``GameConfig()`` defaults
            apply when ``None``.
        seed:
            RNG seed for deterministic shuffle (tests / replays).

        Raises
        ------
        ValueError
            If ``len(player_ids) != 2`` or ``len(deck) != 40``.
        """
        if len(player_ids) != 2:
            raise ValueError(
                f"Scopa requires exactly 2 players, got {len(player_ids)}."
            )
        if len(deck) != 40:
            raise ValueError(
                f"Deck must contain exactly 40 cards, got {len(deck)}."
            )

        cfg = config or GameConfig()

        shuffled = list(deck)
        rng = random.Random(seed)
        rng.shuffle(shuffled)

        players = [
            PlayerState(id=pid, hand=[], captured=[], scopas=0)
            for pid in player_ids
        ]

        state = GameState(
            deck=shuffled,
            table=[],
            players=players,
            current_player_index=0,
            last_capture_player_id=None,
            scores={pid: 0 for pid in player_ids},
            phase="playing",
            config=cfg,
        )

        # Deal initial hands + table cards
        state = self._deal_initial(state)
        return state

    def play_card(
        self,
        state: GameState,
        player_id: str,
        card_id: str,
        capture_ids: list[str],
    ) -> GameState:
        """
        Execute one move: play *card_id* from *player_id*'s hand, optionally
        capturing the table cards identified by *capture_ids*.

        Parameters
        ----------
        state:
            Current game state.
        player_id:
            ID of the acting player.
        card_id:
            ``Card.id`` of the card to play from the hand.
        capture_ids:
            ``Card.id`` values of the table cards to capture.  Pass an empty
            list to discard (lay the card on the table without capturing).

        Returns
        -------
        GameState
            New state after the move has been applied.

        Raises
        ------
        WrongTurnError
            If *player_id* is not the current player.
        CardNotInHandError
            If *card_id* is not in the player's hand.
        InvalidCaptureError
            If *capture_ids* does not form a legal capture.
        EqualValuePriorityError
            If the player attempts a sum capture when an exact match exists.
        """
        state = self._deep_copy_state(state)

        # ── Turn validation ───────────────────────────────────────────────────
        expected_id = state.current_player.id
        if player_id != expected_id:
            raise WrongTurnError(acting=player_id, expected=expected_id)

        player = state.player_by_id(player_id)

        # ── Find played card in hand ──────────────────────────────────────────
        played_card = self._find_card_in_list(card_id, player.hand)
        if played_card is None:
            raise CardNotInHandError(card_id=card_id, player_id=player_id)

        # ── Validate capture ──────────────────────────────────────────────────
        capture_cards = self._validate_capture(
            played_card, capture_ids, state.table
        )

        # ── Apply move ────────────────────────────────────────────────────────
        player.hand.remove(played_card)

        if capture_cards:
            # Remove captured cards from table
            for c in capture_cards:
                state.table.remove(c)
            # Award played card + captured cards to player
            player.captured.append(played_card)
            player.captured.extend(capture_cards)
            state.last_capture_player_id = player_id

            # Scopa check — cannot score scopa on the very last round capture
            # (taking the last card as end-of-round sweep is not a scopa)
            if not state.table and state.deck:
                state = self._apply_scopa(state, player_id)
        else:
            # Discard — card goes face-up on the table
            state.table.append(played_card)

        state = self._advance_turn(state)
        return state

    def deal_if_needed(self, state: GameState) -> GameState:
        """
        Deal a new round of hands when all players' hands are empty and cards
        remain in the deck.

        This is a no-op when:
        * Any player still holds cards in hand.
        * The deck is already empty.

        Returns
        -------
        GameState
            State with freshly dealt hands, or the unchanged state.
        """
        if state.deck and all(len(p.hand) == 0 for p in state.players):
            state = self._deep_copy_state(state)
            state = self._deal_hands(state)
        return state

    def is_round_over(self, state: GameState) -> bool:
        """
        Return ``True`` when the round is over.

        A round ends when the deck is empty **and** all players' hands are
        empty (all 40 cards have been played or are on the table).
        """
        return (
            len(state.deck) == 0
            and all(len(p.hand) == 0 for p in state.players)
        )

    def calculate_round_score(self, state: GameState) -> GameState:
        """
        Finalise the round: award remaining table cards, compute all scoring
        categories, and transition to ``"finished"`` phase.

        The caller should persist ``state.scores`` before starting a new round
        if tracking multi-round totals.

        Returns
        -------
        GameState
            State in ``"finished"`` phase with ``scores`` populated.

        Raises
        ------
        ScopaEngineError
            If called before the round is over (``is_round_over`` is ``False``).
        """
        if not self.is_round_over(state):
            raise ScopaEngineError(
                "calculate_round_score called before the round is over."
            )

        state = self._deep_copy_state(state)

        # ── Award remaining table cards to last capturer ───────────────────────
        if state.table and state.last_capture_player_id:
            last_capturer = state.player_by_id(state.last_capture_player_id)
            last_capturer.captured.extend(state.table)
            state.table = []
        elif state.table:
            # Edge case: nobody ever captured (impossible in standard play but
            # handle defensively — cards are simply discarded).
            state.table = []

        # ── Scoring ───────────────────────────────────────────────────────────
        cfg = state.config

        captured_counts = {p.id: len(p.captured) for p in state.players}
        coins_counts    = {
            p.id: sum(1 for c in p.captured if c.suit == cfg.coins_suit)
            for p in state.players
        }
        has_settebello  = {
            p.id: any(
                c.suit == cfg.coins_suit and c.value == 7
                for c in p.captured
            )
            for p in state.players
        }
        primiera_scores = {p.id: self._calculate_primiera(p, cfg) for p in state.players}

        additions: dict[str, int] = {p.id: 0 for p in state.players}

        # Most captured cards (tie → nobody scores)
        additions = self._award_most(additions, captured_counts)

        # Most coins (tie → nobody scores)
        additions = self._award_most(additions, coins_counts)

        # Settebello
        for pid, has in has_settebello.items():
            if has:
                additions[pid] += 1

        # Primiera (highest total primiera score wins; tie → nobody scores)
        additions = self._award_most(additions, primiera_scores)

        # Accumulated scopas (+1 each)
        for p in state.players:
            additions[p.id] += p.scopas

        # Write final scores
        for pid, pts in additions.items():
            state.scores[pid] = pts

        state.phase = "finished"
        return state

    # ── Private helpers: validation ───────────────────────────────────────────

    def _validate_capture(
        self,
        played_card: Card,
        capture_ids: list[str],
        table: list[Card],
    ) -> list[Card]:
        """
        Validate the proposed capture and return the cards to be captured.

        Returns an empty list when *capture_ids* is empty (discard move).

        Rules enforced
        --------------
        1. All *capture_ids* must reference cards actually on the table.
        2. The captured cards must sum to ``played_card.value`` **or** be a
           single card with the same value.
        3. If an exact-value match exists on the table, a sum-combination
           capture is forbidden (**equal-value priority rule**).

        Raises
        ------
        InvalidCaptureError, EqualValuePriorityError
        """
        if not capture_ids:
            return []

        # Resolve IDs → cards
        table_by_id: dict[str, Card] = {c.id: c for c in table}
        missing = [cid for cid in capture_ids if cid not in table_by_id]
        if missing:
            raise InvalidCaptureError(
                reason=f"card(s) not on table: {missing}",
                card_id=played_card.id,
                capture_ids=capture_ids,
            )

        capture_cards = [table_by_id[cid] for cid in capture_ids]
        capture_sum = sum(c.value for c in capture_cards)

        if capture_sum != played_card.value:
            raise InvalidCaptureError(
                reason=(
                    f"captured values sum to {capture_sum}, "
                    f"played card value is {played_card.value}"
                ),
                card_id=played_card.id,
                capture_ids=capture_ids,
            )

        # Equal-value priority: if a single table card matches the played
        # value, the player MUST capture it — sum combinations are illegal.
        if len(capture_cards) > 1:
            exact_match = next(
                (c for c in table if c.value == played_card.value), None
            )
            if exact_match is not None:
                raise EqualValuePriorityError(
                    card_id=played_card.id,
                    matching_id=exact_match.id,
                )

        return capture_cards

    def _find_sum_combinations(
        self,
        target: int,
        table: list[Card],
    ) -> list[list[Card]]:
        """
        Return all subsets of *table* whose values sum to *target*.

        Used externally (e.g. AI / hint systems) to enumerate legal captures.
        The result excludes single-card exact matches — those are handled by
        the equal-value priority rule.

        Parameters
        ----------
        target:
            The value of the played card.
        table:
            Current face-up table cards.

        Returns
        -------
        list[list[Card]]
            All valid capture subsets (may be empty).
        """
        results: list[list[Card]] = []

        # Single-card exact match (separate from sum combinations)
        for card in table:
            if card.value == target:
                results.append([card])
                return results  # exact match found → only legal option

        # Multi-card sum combinations
        for size in range(2, len(table) + 1):
            for combo in combinations(table, size):
                if sum(c.value for c in combo) == target:
                    results.append(list(combo))

        return results

    # ── Private helpers: scoring ──────────────────────────────────────────────

    def _calculate_primiera(self, player: PlayerState, cfg: GameConfig) -> int:
        """
        Calculate this player's total primiera score.

        Primiera assigns each player the *best* (highest-scoring) card per
        suit across their captured cards.  The player with the higher total
        wins the primiera point.

        Only suits that the player holds at least one card of contribute.
        A player with no cards in a suit scores 0 for that suit (meaning they
        cannot win primiera if the opponent holds cards in all four suits).

        Returns
        -------
        int
            Sum of best primiera values across all four standard suits.
        """
        suits = ("bastoni", "coppe", "oro", "spade")
        total = 0
        for suit in suits:
            suit_cards = [c for c in player.captured if c.suit == suit]
            if suit_cards:
                best = max(cfg.primiera_score(c.value) for c in suit_cards)
                total += best
        return total

    def _apply_scopa(self, state: GameState, player_id: str) -> GameState:
        """
        Increment *player_id*'s scopa counter.

        Called only when the table is cleared by a capture **and** the deck
        is not empty (last-hand table clear is not a scopa).

        Returns the modified state (already a deep copy from the caller).
        """
        player = state.player_by_id(player_id)
        player.scopas += 1
        return state

    def _advance_turn(self, state: GameState) -> GameState:
        """
        Move ``current_player_index`` to the next player.

        Wraps around using modulo so the pattern extends naturally if more
        than 2 players are ever supported.
        """
        state.current_player_index = (
            state.current_player_index + 1
        ) % len(state.players)
        return state

    # ── Private helpers: dealing ──────────────────────────────────────────────

    def _deal_initial(self, state: GameState) -> GameState:
        """
        Place ``config.initial_table_size`` cards on the table, then deal
        ``config.hand_size`` cards to each player.

        Called once inside :py:meth:`create_game`.
        """
        cfg = state.config

        # Table cards
        state.table = state.deck[: cfg.initial_table_size]
        state.deck = state.deck[cfg.initial_table_size :]

        # Deal hands — deal one card at a time round-robin (authentic dealing)
        for _ in range(cfg.hand_size):
            for player in state.players:
                if state.deck:
                    player.hand.append(state.deck.pop(0))

        return state

    def _deal_hands(self, state: GameState) -> GameState:
        """
        Deal ``config.hand_size`` cards to each player from the deck.

        Called by :py:meth:`deal_if_needed` when all hands are empty.
        No new table cards are dealt mid-round (only at game start).
        """
        cfg = state.config
        for _ in range(cfg.hand_size):
            for player in state.players:
                if state.deck:
                    player.hand.append(state.deck.pop(0))
        return state

    # ── Private helpers: utilities ────────────────────────────────────────────

    @staticmethod
    def _find_card_in_list(card_id: str, cards: list[Card]) -> Optional[Card]:
        """Return the first card in *cards* with ``Card.id == card_id``, or ``None``."""
        return next((c for c in cards if c.id == card_id), None)

    @staticmethod
    def _award_most(
        additions: dict[str, int],
        counts: dict[str, int],
    ) -> dict[str, int]:
        """
        Award 1 point to the player with the strictly highest count.

        Ties result in no points being awarded for that category.

        Parameters
        ----------
        additions:
            Running point totals, mutated in place (already a copy).
        counts:
            Per-player numeric score for a single scoring category.
        """
        if not counts:
            return additions
        max_val = max(counts.values())
        winners = [pid for pid, v in counts.items() if v == max_val]
        if len(winners) == 1:
            additions[winners[0]] += 1
        return additions

    @staticmethod
    def _deep_copy_state(state: GameState) -> GameState:
        """
        Return a deep copy of *state* so the engine never mutates caller data.

        ``Card`` objects themselves are frozen dataclasses — they are safe to
        share without copying.  Only the mutable container objects (lists,
        dicts, :class:`PlayerState`) need duplication.
        """
        new_players = [
            PlayerState(
                id=p.id,
                hand=list(p.hand),
                captured=list(p.captured),
                scopas=p.scopas,
            )
            for p in state.players
        ]
        return GameState(
            deck=list(state.deck),
            table=list(state.table),
            players=new_players,
            current_player_index=state.current_player_index,
            last_capture_player_id=state.last_capture_player_id,
            scores=dict(state.scores),
            phase=state.phase,
            config=state.config,  # frozen dataclass — safe to share
        )
