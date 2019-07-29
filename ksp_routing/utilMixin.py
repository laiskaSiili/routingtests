import inspect
import os

class UtilMixin:

    def __init__(self):
        self.settings = {
            'os_sep': os.sep,
        }

    def get_settings(self):
        return self.settings

    def get_data(self):
        return self.data

    def _print(self, prefix='INFO', msg='Calling this'):
        data = {
            'prefix': prefix,
            'cls': self.__class__.__name__,
            'fn': inspect.stack()[1].function,
            'msg': msg
        }
        print('{prefix}: {cls} -> {fn}: {msg}'. format(**data))

    def _create_workspace_if_not_exists(self):
        self._print()
        path = self.settings['workspace_path']
        if not os.path.isdir(path):
            abs_path = os.path.abspath(path)
            msg = 'Workspace directory not found: {path} | ' \
                  'Creating directory {abs_path}'.format(path=path, abs_path=abs_path)
            self._print(prefix='WARNING', msg=msg)
            os.mkdir(path)
            self._print(msg='Successfully created workspace directory {path}'.format(path=path))
