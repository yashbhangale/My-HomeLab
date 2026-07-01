
Re-add the shared-media volume mapping for Chrome (Workspaces → Chrome → Volume Mapping):


{"/srv/media": {"bind": "/home/kasm-user/Downloads/media", "mode": "rw", "uid": 1000, "gid": 1000, "required": true}}
