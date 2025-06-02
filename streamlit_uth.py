import streamlit as st
from treys import Card, Evaluator
from itertools import combinations
import os

###########################
# 1) Must be FIRST: set_page_config
###########################
st.set_page_config(layout="wide")

###########################
# 2) Custom CSS to style
###########################
CUSTOM_CSS = """
<style>
/* Make the P/B/D buttons as thin as possible */
button[data-baseweb="button"] {
  padding: 0.15rem 0.3rem !important;
  min-height: 0 !important;
  line-height: 1.0 !important;
}
/* Prevent card images from having rounded corners */
img {
  border-radius: 0 !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

###########################
# 3) Ultimate Texas Hold’em Solver
###########################
evaluator = Evaluator()


def create_treys_full_deck():
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    suits = ['c', 'd', 'h', 's']
    return [Card.new(r + s) for r in ranks for s in suits]


def dealer_qualifies(dealer_7):
    val = evaluator.evaluate([], dealer_7)
    rclass = evaluator.get_rank_class(val)
    return (rclass <= 9)  # Pair or better


def compare_hands(player_7, dealer_7):
    pval = evaluator.evaluate([], player_7)
    dval = evaluator.evaluate([], dealer_7)
    if pval < dval:
        return 1
    elif pval > dval:
        return -1
    else:
        return 0


def hand_category_0to9(cards7):
    val = evaluator.evaluate([], cards7)
    rclass = evaluator.get_rank_class(val)
    return 10 - rclass  # 9=Royal,...,0=HC


def blind_payout_multiplier(cat_0to9):
    # Typical Blind pay table
    if cat_0to9 == 9:  # Royal
        return 500
    elif cat_0to9 == 8:  # SF
        return 50
    elif cat_0to9 == 7:  # 4K
        return 10
    elif cat_0to9 == 6:  # FH
        return 3
    elif cat_0to9 == 5:  # Flush
        return 3
    elif cat_0to9 == 4:  # Straight
        return 1
    else:
        return 0


def payout_final_decision(player_7, dealer_7, ante, blind, play):
    dq = dealer_qualifies(dealer_7)
    outcome = compare_hands(player_7, dealer_7)
    cat = hand_category_0to9(player_7)

    net = 0.0
    # PLAY
    if outcome > 0:
        net += play
    elif outcome < 0:
        net -= play

    # ANTE
    if dq:
        if outcome > 0:
            net += ante
        elif outcome < 0:
            net -= ante

    # BLIND
    if outcome > 0:
        multi = blind_payout_multiplier(cat)
        if multi > 0:
            net += multi * blind
    elif outcome < 0:
        net -= blind
    return net


def river_ev_compare_treys(hole_cards, board_cards, dead_cards):
    """
    Compare EV of fold vs bet 1x at the river,
    with ante=1.0 and blind=1.0 (no user override).
    """
    ante = 1.0
    blind = 1.0

    full_deck = create_treys_full_deck()
    known = set(hole_cards + board_cards + dead_cards)
    remaining_deck = [c for c in full_deck if c not in known]

    player_7 = hole_cards + board_cards
    dealer_combos = list(combinations(remaining_deck, 2))

    ev_fold = -(ante + blind)
    sum_bet = 0.0
    for dc in dealer_combos:
        dealer_7 = list(dc) + board_cards
        payoff = payout_final_decision(player_7, dealer_7, ante, blind, ante)
        sum_bet += payoff

    ev_bet = sum_bet / len(dealer_combos) if dealer_combos else 0.0
    delta_ev = ev_bet - ev_fold
    rec = "BET 1X" if delta_ev > 0 else "FOLD"
    return {
        "EV_bet": ev_bet,
        "EV_fold": ev_fold,
        "Delta_EV": delta_ev,
        "Recommended": rec
    }


###########################
# 4) Display Helpers
###########################
def show_slot_image(card_int_or_none):
    """
    If None -> show 'empty_card.png'.
    Else -> show the card's PNG (width=45).
    """
    if card_int_or_none is None:
        empty_path = os.path.join("cards", "empty_card.png")
        if os.path.exists(empty_path):
            st.image(empty_path, width=45)
        else:
            st.write("[Empty Slot]")
    else:
        label = Card.int_to_str(card_int_or_none).lower()
        path = os.path.join("cards", f"{label}.png")
        if os.path.exists(path):
            st.image(path, width=45)
        else:
            st.write(label)


def display_fixed_slots(title_str, cards_list, capacity, prefix):
    """
    Show 'capacity' horizontal slots (like 2 for hole, 5 for board, 10 for dead).
    Each slot has an image (the card or empty).
    If there's a card in the slot, we also show an 'x' button below it
    in the same column. The button is container-width, matching the image width.
    """
    st.write(f"**{title_str}**")
    # e.g. capacity=2 => create 3 columns: 2 columns each 0.07 wide + leftover
    col_widths = [0.07] * capacity + [max(0, 1 - 0.07 * capacity)]
    cols = st.columns(col_widths, gap="small")

    for i in range(capacity):
        if i >= len(cols) - 1:
            break
        with cols[i]:
            if i < len(cards_list):
                c_int = cards_list[i]
                show_slot_image(c_int)
                # Now the 'x' button (same column, container_width)
                if st.button("❌", key=f"{prefix}_remove_{c_int}", use_container_width=True):
                    cards_list.remove(c_int)
                    st.rerun()
            else:
                # empty
                show_slot_image(None)


###########################
# 5) Main
###########################
def main():
    # Title row: left is heading, right is 'Clear All'
    top_bar = st.columns([0.8, 0.2], gap="small")
    with top_bar[0]:
        st.title("UTH - River Solver")
    with top_bar[1]:
        if st.button("Clear All"):
            st.session_state.hole_cards = []
            st.session_state.board_cards = []
            st.session_state.dead_cards = []
            st.rerun()

    # Init session state
    if "hole_cards" not in st.session_state:
        st.session_state.hole_cards = []
    if "board_cards" not in st.session_state:
        st.session_state.board_cards = []
    if "dead_cards" not in st.session_state:
        st.session_state.dead_cards = []

    # Auto-calc EV if 2 hole + 5 board
    valid = (len(st.session_state.hole_cards) == 2
             and len(st.session_state.board_cards) == 5)
    ev_container = st.container()
    if valid:
        results = river_ev_compare_treys(
            st.session_state.hole_cards,
            st.session_state.board_cards,
            st.session_state.dead_cards
        )
        with ev_container:
            st.info(f"""**EV if Bet 1x:** {results['EV_bet']:.3f}

**EV if Fold:** {results['EV_fold']:.3f}

**Delta EV:** {results['Delta_EV']:.3f}

**Recommendation:** {results['Recommended']}""")
    else:
        with ev_container:
            st.info("Select exactly 2 PLayer Cards and 5 Board Cards to see EV.")

    st.write("---")
    st.subheader("Currently Selected")

    # 2 Hole, 5 Board, 10 Dead
    display_fixed_slots("Player Cards", st.session_state.hole_cards, 2, "hole")
    display_fixed_slots("Board", st.session_state.board_cards, 5, "board")
    display_fixed_slots("Dead Cards", st.session_state.dead_cards, 10, "dead")

    st.write("---")
    st.subheader("Pick Cards")

    # Hide P/B/D if full
    can_pick_hole = (len(st.session_state.hole_cards) < 2)
    can_pick_board = (len(st.session_state.board_cards) < 5)
    can_pick_dead = (len(st.session_state.dead_cards) < 10)

    # 13 across, 4 down
    ranks = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]
    suits = ["d", "c", "h", "s"]

    for s_i, suit in enumerate(suits):
        row_cols = st.columns(13, gap="small")
        for r_i, rank in enumerate(ranks):
            card_label = rank + suit
            c_int = Card.new(card_label)

            # If already selected, show the same card image but no pick buttons
            if (c_int in st.session_state.hole_cards or
                    c_int in st.session_state.board_cards or
                    c_int in st.session_state.dead_cards):
                # just show the card image
                c_path = os.path.join("cards", f"{card_label.lower()}.png")
                if os.path.exists(c_path):
                    row_cols[r_i].image(c_path, width=45)
                else:
                    row_cols[r_i].write(card_label)
                # no pick button
                continue

            # Not selected => show the card + pick buttons
            c_path = os.path.join("cards", f"{card_label.lower()}.png")
            if os.path.exists(c_path):
                row_cols[r_i].image(c_path, width=45)
            else:
                row_cols[r_i].write(card_label)

            button_row = []
            if can_pick_hole:
                button_row.append(("P", f"p_{card_label}"))
            if can_pick_board:
                button_row.append(("B", f"b_{card_label}"))
            if can_pick_dead:
                button_row.append(("D", f"d_{card_label}"))

            for (txt, key) in button_row:
                clicked = row_cols[r_i].button(txt, key=key)
                if clicked:
                    if txt == "P":
                        st.session_state.hole_cards.append(c_int)
                    elif txt == "B":
                        st.session_state.board_cards.append(c_int)
                    elif txt == "D":
                        st.session_state.dead_cards.append(c_int)
                    st.rerun()


if __name__ == "__main__":
    main()
