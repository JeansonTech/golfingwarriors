"""Small document-head helpers for mobile home-screen metadata."""

import streamlit.components.v1 as components


def inject_pwa_metadata():
    """Register the manifest and Apple touch icon in the Streamlit document."""
    components.html(
        """
        <script>
        (() => {
          const appWindow = window.parent;
          const doc = appWindow.document;
          const appBase = new URL("./", appWindow.location.href);
          const staticBase = new URL("app/static/", appBase);

          const setLink = (id, rel, href, sizes) => {
            let node = doc.getElementById(id);
            if (!node) {
              node = doc.createElement("link");
              node.id = id;
              doc.head.appendChild(node);
            }
            node.rel = rel;
            node.href = href;
            if (sizes) node.sizes = sizes;
          };

          setLink(
            "golfing-warriors-manifest",
            "manifest",
            new URL("manifest.json", staticBase).href
          );
          setLink(
            "golfing-warriors-apple-icon",
            "apple-touch-icon",
            new URL("apple-touch-icon.png", staticBase).href,
            "180x180"
          );

          const setMeta = (name, content) => {
            let node = doc.querySelector(`meta[name="${name}"]`);
            if (!node) {
              node = doc.createElement("meta");
              node.name = name;
              doc.head.appendChild(node);
            }
            node.content = content;
          };
          setMeta("theme-color", "#062f21");
          setMeta("apple-mobile-web-app-title", "Golfing Warriors");
          setMeta("apple-mobile-web-app-capable", "yes");
          setMeta("mobile-web-app-capable", "yes");
        })();
        </script>
        """,
        height=0,
        width=0,
    )
