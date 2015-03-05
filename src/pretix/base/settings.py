import json


DEFAULTS = {
    'user_mail_required': 'False',
    'max_items_per_order': '10',
    'attendee_names_asked': 'True',
    'attendee_names_required': 'False',
}


class SettingsProxy:
    """
    This objects allows convenient access to settings stored in the
    EventSettings/OrganizerSettings database model. It exposes all settings as
    properties and it will do all the nasty inheritance and defaults stuff for
    you. It will return None for non-existing properties.
    """

    def __init__(self, obj, parent=None, type=None):
        self._obj = obj
        self._parent = parent
        self._cached_obj = None
        self._type = type

    def _cache(self):
        if self._cached_obj is None:
            self._cached_obj = {}
            for setting in self._obj.setting_objects.current.all():
                self._cached_obj[setting.key] = setting
        return self._cached_obj

    def _unserialize(self, value, as_type):
        if isinstance(value, as_type):
            return value
        elif as_type == int:
            return int(value)
        elif as_type == float:
            return float(value)
        elif as_type == dict or as_type == list:
            return json.loads(value)
        elif as_type == bool:
            return value == 'True'
        return value

    def _serialize(self, value):
        if isinstance(value, str):
            return value
        elif isinstance(value, int) or isinstance(value, float) or isinstance(value, bool):
            return str(value)
        elif isinstance(value, list) or isinstance(value, bool):
            return json.dumps(value)
        raise TypeError('Unable to serialize %s into a setting.' % str(type(value)))

    def get(self, key, default=None, as_type=str):
        """
        Get a setting specified by key 'key'. Normally, settings are strings, but
        if you put non-strings into the settings object, you can request unserialization
        by specifying 'as_type'
        """
        if key in self._cache():
            return self._unserialize(self._cache()[key].value, as_type)
        value = None
        if self._parent:
            value = self._parent.settings.get(key)
        if value is None and key in DEFAULTS:
            return self._unserialize(DEFAULTS[key], as_type)
        if value is None and default is not None:
            return self._unserialize(default, as_type)
        return self._unserialize(value, as_type)

    def __getitem__(self, key):
        return self.get(key)

    def __getattr__(self, key):
        return self.get(key)

    def __setattr__(self, key, value):
        if key.startswith('_'):
            return super().__setattr__(key, value)
        self.set(key, value)

    def __setitem__(self, key, value):
        self.set(key, value)

    def set(self, key, value):
        if key in self._cache():
            s = self._cache()[key]
            s = s.clone()
        else:
            s = self._type(object=self._obj, key=key)
        s.value = self._serialize(value)
        s.save()
        self._cache()[key] = s

    def __delattr__(self, key):
        if key.startswith('_'):
            return super().__delattr__(key)
        return self.__delitem__(key)

    def __delitem__(self, key):
        if key in self._cache():
            self._cache()[key].delete()
            del self._cache()[key]


class SettingsSandbox:
    """
    Transparently proxied access to event settings, handling your domain-
    prefixes for you.
    """

    def __init__(self, type, key, event):
        self._event = event
        self._type = type
        self._key = key

    def _convert_key(self, key):
        return '%s_%s_%s' % (self._type, self._key, key)

    def __setitem__(self, key, value):
        self.set(key, value)

    def __setattr__(self, key, value):
        if key.startswith('_'):
            return super().__setattr__(key, value)
        self.set(key, value)

    def __getattr__(self, item):
        return self.get(item)

    def __getitem__(self, item):
        return self.get(item)

    def __delitem__(self, key):
        del self._event.settings[self._convert_key(key)]

    def __delattr__(self, key):
        del self._event.settings[self._convert_key(key)]

    def get(self, key, default=None, as_type=str):
        return self._event.settings.get(self._convert_key(key), default=default, as_type=type)

    def set(self, key, value):
        self._event.settings.set(self._convert_key(key), value)