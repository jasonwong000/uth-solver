import streamlit as st
from treys import Card, Evaluator
from itertools import combinations
import os

###########################
# 1) Must be FIRST: set_page_config
###########################
st.set_page_config(layout="wide")

###########################
# 2) Custom CSS
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
    return (evaluator.get_rank_class(val) <= 9)


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
    return 10 - rclass


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
    if outcome > 0:
        net += play
    elif outcome < 0:
        net -= play

    if dq:
        if outcome > 0:
            net += ante
        elif outcome < 0:
            net -= ante

    if outcome > 0:
        multi = blind_payout_multiplier(cat)
        if multi > 0:
            net += multi * blind
    elif outcome < 0:
        net -= blind
    return net


def river_ev_compare_treys(player_cards, board_cards, dead_cards):
    ante = 1.0
    blind = 1.0

    deck = create_treys_full_deck()
    known = set(player_cards + board_cards + dead_cards)
    remaining = [c for c in deck if c not in known]

    combos = list(combinations(remaining, 2))
    ev_fold = -(ante + blind)
    sum_bet = 0.0

    player_7 = player_cards + board_cards
    for dc in combos:
        dealer_7 = list(dc) + board_cards
        payoff = payout_final_decision(player_7, dealer_7, ante, blind, ante)
        sum_bet += payoff

    ev_bet = sum_bet / len(combos) if combos else 0.0
    delta_ev = ev_bet - ev_fold
    rec = "BET 1X" if delta_ev > 0 else "FOLD"
    return {
        "EV_bet": ev_bet,
        "EV_fold": ev_fold,
        "Delta_EV": delta_ev,
        "Recommended": rec
    }


###########################
# 4) Suit Colors:
#    Diamonds & Hearts => Red
#    Clubs & Spades => Grey
###########################
SUIT_SYMBOLS = {
    'c': '♣',
    'd': '♦',
    'h': '♥',
    's': '♠'
}


def suit_color(suit_char):
    """
    - clubs (c) = grey
    - diamonds (d) = red
    - hearts (h) = red
    - spades (s) = grey
    """
    if suit_char in ['d', 'h']:
        return 'red'
    else:
        return 'grey'  # c or s


def get_colored_card_str(card_int):
    """ e.g. <span style="color:red">A♦</span> for Ad; clubs/spades => grey """
    c_str = Card.int_to_str(card_int)  # e.g. "As"
    rank, suit = c_str[0], c_str[1]
    ascii_suit = SUIT_SYMBOLS[suit]
    color = suit_color(suit)
    return f'<span style="color:{color}">{rank}{ascii_suit}</span>'


def get_card_line(cards):
    return ' '.join(get_colored_card_str(c) for c in cards)


def generate_first_line(player_cards, board_cards, dead_cards):
    p_str = get_card_line(player_cards)
    b_str = get_card_line(board_cards)
    d_str = get_card_line(dead_cards)
    return f"{p_str} | {b_str} | {d_str}"


###########################
# 5) Display placeholders
###########################
def show_slot_image(card_int_or_none):
    if card_int_or_none is None:
        path = os.path.join("cards", "empty_card.png")
        if os.path.exists(path):
            st.image(path, width=45)
        else:
            st.write("[Empty Slot]")
    else:
        label = Card.int_to_str(card_int_or_none)
        fname = f"{label.lower()}.png"
        path = os.path.join("cards", fname)
        if os.path.exists(path):
            st.image(path, width=45)
        else:
            st.write(label.lower())


def display_fixed_slots(title_str, cards_list, capacity, prefix):
    st.write(f"**{title_str}**")
    col_widths = [0.07] * capacity + [max(0, 1 - 0.07 * capacity)]
    cols = st.columns(col_widths, gap="small")
    for i in range(capacity):
        if i >= len(cols) - 1:
            break
        with cols[i]:
            if i < len(cards_list):
                c_int = cards_list[i]
                show_slot_image(c_int)
                if st.button("❌", key=f"{prefix}_remove_{c_int}", use_container_width=True):
                    cards_list.remove(c_int)
                    st.rerun()
            else:
                show_slot_image(None)


###########################
# 6) Main
###########################
def main():
    top_bar = st.columns([0.8, 0.2], gap="small")
    with top_bar[0]:
        st.title("UTH - River Solver")
    with top_bar[1]:
        if st.button("Clear All"):
            st.session_state.player_cards = []
            st.session_state.board_cards = []
            st.session_state.dead_cards = []
            st.rerun()

    if "player_cards" not in st.session_state:
        st.session_state.player_cards = []
    if "board_cards" not in st.session_state:
        st.session_state.board_cards = []
    if "dead_cards" not in st.session_state:
        st.session_state.dead_cards = []

    # 4-colored suit line
    first_line_html = generate_first_line(
        st.session_state.player_cards,
        st.session_state.board_cards,
        st.session_state.dead_cards
    )

    st.markdown(first_line_html, unsafe_allow_html=True)

    valid = (len(st.session_state.player_cards) == 2
             and len(st.session_state.board_cards) == 5)
    if valid:
        res = river_ev_compare_treys(
            st.session_state.player_cards,
            st.session_state.board_cards,
            st.session_state.dead_cards
        )
        st.info(f"""**EV if Bet 1x:** {res['EV_bet']:.3f}

**EV if Fold:** {res['EV_fold']:.3f}

**Delta EV:** {res['Delta_EV']:.3f}

**Recommendation:** {res['Recommended']}""")
    else:
        st.info("Select exactly 2 Player Cards and 5 Board Cards to see EV.")

    st.write("---")
    st.subheader("Currently Selected")

    display_fixed_slots("Player Cards", st.session_state.player_cards, 2, "player")
    display_fixed_slots("Board", st.session_state.board_cards, 5, "board")
    display_fixed_slots("Dead Cards", st.session_state.dead_cards, 10, "dead")

    st.write("---")
    st.subheader("Pick Cards")

    can_pick_player = (len(st.session_state.player_cards) < 2)
    can_pick_board = (len(st.session_state.board_cards) < 5)
    can_pick_dead = (len(st.session_state.dead_cards) < 10)

    ranks = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]
    suits = ["d", "c", "h", "s"]

    for s_i, suit in enumerate(suits):
        row_cols = st.columns(13, gap="small")
        for r_i, rank in enumerate(ranks):
            card_label = rank + suit
            c_int = Card.new(card_label)

            if (c_int in st.session_state.player_cards or
                    c_int in st.session_state.board_cards or
                    c_int in st.session_state.dead_cards):
                fname = f"{card_label.lower()}.png"
                c_path = os.path.join("cards", fname)
                if os.path.exists(c_path):
                    row_cols[r_i].image(c_path, width=45)
                else:
                    row_cols[r_i].write(card_label.lower())
                continue

            fname = f"{card_label.lower()}.png"
            c_path = os.path.join("cards", fname)
            if os.path.exists(c_path):
                row_cols[r_i].image(c_path, width=45)
            else:
                row_cols[r_i].write(card_label.lower())

            button_row = []
            if can_pick_player:
                button_row.append(("P", f"p_{card_label}"))
            if can_pick_board:
                button_row.append(("B", f"b_{card_label}"))
            if can_pick_dead:
                button_row.append(("D", f"d_{card_label}"))

            for (txt, key) in button_row:
                clicked = row_cols[r_i].button(txt, key=key)
                if clicked:
                    if txt == "P":
                        st.session_state.player_cards.append(c_int)
                    elif txt == "B":
                        st.session_state.board_cards.append(c_int)
                    elif txt == "D":
                        st.session_state.dead_cards.append(c_int)
                    st.rerun()


if __name__ == "__main__":
    main()
