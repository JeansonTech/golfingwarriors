Golfing Warriors event formats and mobile icon update

Replace the matching repository paths in this bundle.

Events now have one official IPS or NET format and optional IPS, NET, and Match Play side games. The official format determines final positions and ranking points. Match Play keeps the existing Teams/Singles pairing setup and is configured alongside scoring fourballs.

The database initialization adds event_competitions and keeps IPS and NET boards enabled for existing events. Existing Match Play pairings are retained and detected.

For mobile home-screen icons, this bundle includes the Streamlit static-serving config, an Android web app manifest and 192/512 icons, and an iOS 180px Apple touch icon. pwa.py inserts manifest and Apple icon links into the page head. After deploying, remove the existing phone shortcut and add it again so the phone refreshes its cached icon.

The app uses HTTPS when installed as a home-screen web app. No offline service worker is included.
