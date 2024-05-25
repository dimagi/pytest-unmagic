from unmagic import fence

fence.install([__package__])
pytest_plugins = [
    "pytester",
    "unmagic.scope",
]
