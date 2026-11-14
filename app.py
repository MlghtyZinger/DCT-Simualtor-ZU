"""Abu Dhabi Visitor Insights – main page.
Travelers: open to everyone (guest).   DCT dashboard: admins only (sign-in).
The admin username/password are kept in Streamlit "Secrets", never in this code.
"""
import hmac
import streamlit as st

st.set_page_config(page_title="Abu Dhabi Visitor Insights", page_icon="🏙️", layout="wide")


def admin_login_details():
    try:
        return st.secrets["admin"]["username"], st.secrets["admin"]["password"]
    except Exception:
        return None


def welcome():
    st.title("🏙️ Abu Dhabi Visitor Insights")
    st.caption("Trip planning for travelers, and the forecasting dashboard for DCT.")
    left, right = st.columns(2, gap="large")

    with left, st.container(border=True):
        st.subheader("🧳 I'm a traveler")
        st.write("Find out when Abu Dhabi is quiet or busy, and when the weather is best.")
        if st.button("Continue as guest", type="primary"):
            st.switch_page(traveler)

    with right, st.container(border=True):
        st.subheader("🔒 DCT admin")
        if st.session_state.get("is_admin"):
            st.success("You are signed in.")
            if st.button("Open DCT dashboard"):
                st.switch_page(dashboard)
            return
        details = admin_login_details()
        if details is None:
            st.warning("Admin sign-in is not set up yet. Add the [admin] username and password "
                       "in Streamlit Cloud → App settings → Secrets.")
        with st.form("login"):
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            sent = st.form_submit_button("Sign in")
        if sent:
            if details and hmac.compare_digest(user, details[0]) and hmac.compare_digest(pw, details[1]):
                st.session_state.is_admin = True
                st.switch_page(dashboard)
            else:
                st.error("Wrong username or password.")


home = st.Page(welcome, title="Welcome", icon="🏠", default=True)
traveler = st.Page("traveler_page.py", title="Traveler", icon="🧳", url_path="traveler")
dashboard = st.Page("dct_dashboard.py", title="DCT dashboard", icon="📊", url_path="dct")

# the DCT dashboard only appears in the menu after an admin signs in
pages = [home, traveler] + ([dashboard] if st.session_state.get("is_admin") else [])

if st.session_state.get("is_admin"):
    with st.sidebar:
        st.caption("Signed in as **admin**")
        if st.button("Sign out"):
            st.session_state.is_admin = False
            st.rerun()

st.navigation(pages).run()
