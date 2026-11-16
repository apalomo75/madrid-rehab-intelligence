"""Exercise preserved analyst screens through the explicitly enabled local route."""

from streamlit.testing.v1 import AppTest


def technical_app(route, timeout=120):
    app = AppTest.from_string(
        "import os\nfrom unittest.mock import patch\n"
        'with patch.dict(os.environ, {"MADRID_REHAB_DEV": "1", "MADRID_REHAB_PUBLIC": "0", "MADRID_REHAB_DEMO": "0"}):\n'
        "    from madrid_rehab.city_app import main\n    main()\n",
        default_timeout=timeout,
    ).run()
    return app.selectbox(key="technical_navigation").set_value(route).run()
