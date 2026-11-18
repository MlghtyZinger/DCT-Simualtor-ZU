"""Abu Dhabi Visitor Insights – main page.
Travelers: open to everyone (guest).   DCT dashboard: admins only (sign-in).
The admin username/password are kept in Streamlit "Secrets", never in this code.
"""
import hmac
import streamlit as st

import style

st.set_page_config(page_title="Abu Dhabi Visitor Insights", page_icon=":material/travel_explore:", layout="wide")
style.theme_switch()
style.apply()


def admin_login_details():
    try:
        return st.secrets["admin"]["username"], st.secrets["admin"]["password"]
    except Exception:
        return None


def welcome():
    st.title("Abu Dhabi Visitor Insights", anchor=False)
    st.markdown("<p class='adh-muted' style='font-size:1.0625rem;margin-top:-4px'>"
                "Crowds, weather and events in Abu Dhabi at a glance</p>", unsafe_allow_html=True)
    st.write("")
    left, right = st.columns(2, gap="large")

    with left, st.container(border=True, height=280):
        st.subheader(":material/luggage: Plan a trip", anchor=False)
        st.write("See how busy and how hot your dates will be. No account needed")
        st.write("")
        if st.button("Continue as guest", type="primary", icon=":material/arrow_forward:"):
            st.switch_page(traveler)

    with right, st.container(border=True, height=280):
        st.subheader(":material/lock: DCT staff", anchor=False)
        if st.session_state.get("is_admin"):
            st.write("You are signed in")
            if st.button("Open DCT dashboard", type="primary", icon=":material/arrow_forward:"):
                st.switch_page(dashboard)
            return
        details = admin_login_details()
        if details is None:
            st.warning("Admin sign-in is not set up yet. Add the [admin] username and password "
                       "in Streamlit Cloud → App settings → Secrets")
        with st.form("login", border=False):
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            sent = st.form_submit_button("Sign in")
        if sent:
            if details and hmac.compare_digest(user, details[0]) and hmac.compare_digest(pw, details[1]):
                st.session_state.is_admin = True
                st.switch_page(dashboard)
            else:
                st.error("Wrong username or password")

    st.caption(":material/info: Crowd levels and weather are estimates and may not be fully accurate")


home = st.Page(welcome, title="Welcome", icon=":material/home:", default=True)
traveler = st.Page("traveler_page.py", title="Plan a trip", icon=":material/luggage:", url_path="traveler")
dashboard = st.Page("dct_dashboard.py", title="DCT dashboard", icon=":material/insights:", url_path="dct")

# the DCT dashboard only appears in the menu after an admin signs in
pages = [home, traveler] + ([dashboard] if st.session_state.get("is_admin") else [])

if st.session_state.get("is_admin"):
    with st.sidebar:
        st.caption("Signed in as admin")
        if st.button("Sign out", icon=":material/logout:"):
            st.session_state.is_admin = False
            st.rerun()

st.navigation(pages).run()
