# filter_plugins/sanity_filters.py

def extract_count(item, key):
    if not isinstance(item, dict):
        return 0
    if key not in item:
        return 0
    value = item[key]
    if isinstance(value, list):
        return len(value)
    return 0

class FilterModule(object):
    def filters(self):
        return {
            'extract_count': extract_count
        }

