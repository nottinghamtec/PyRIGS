import urllib.parse


class AssetIDConverter:  # Forces lowercase to uppercase
    regex = '[^/]+'

    def to_python(self, value):
        return str(value).upper()

    def to_url(self, value):
        return str(value).upper()


class ListConverter:
    regex = '[^/]+'

    def to_python(self, value):
        return value.split(',')

    def to_url(self, value):
        string = ""
        for i in value:
            string += "," + str(i)
        return string[1:]
