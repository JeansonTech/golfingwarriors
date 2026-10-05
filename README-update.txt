Golfing Warriors update

Replace the matching paths in the repository with the files in this bundle.

The update adds a main IPS/NET competition and selectable IPS, NET, and Match Play side games. The main format remains the event's official format and determines final positions and ranking points. Match Play retains its separate Teams/Singles pairing setup; scoring fourballs are configured alongside it.

The app now stores selected scoreboards in event_competitions. Database initialization creates this table and backfills both IPS and NET for existing events so their current leaderboard visibility is retained. Existing Match Play setups are backfilled when available.

The repository did not contain a PWA manifest or custom icon assets. The bundle adds assets/golfing-warriors-icon.png and configures the Streamlit page favicon to use it on active app pages. Streamlit documents page_icon as the page favicon; a separate PWA manifest was not present to edit.
