from setuptools import setup

setup(
    name = "Ghost Runner (not ready for production)",
    options = {
        "build_apps": {
            "gui_apps": {
                "ghost-runner": "main.py"
            },
            "include_patterns": [
                "assets/**/*",
                "*.txt",
                "render_pipeline/**/*"
            ],
            "plugins": [
                "pandagl",
                "p3openal_audio"
            ],
            "log_filename": "$USER_APPDATA/ghost-runner/output.log",
            "log_append": False
        }
    }
)
