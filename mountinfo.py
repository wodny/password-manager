#!/usr/bin/python
# -*- coding: utf-8 -*-

import os.path
import sys

class Mount:
    def __init__(self, mountinfoline):
        line = mountinfoline.strip()
        tokens = line.split()
        (self.mountid, self.parentid, self.majmin, root, mountpoint, self.mountopts) = tokens[0:6]
        (sep, self.fstype, self.source, self.superopts) = tokens[-4:]
        self.optional = tokens[6:-4]
        if sep != "-":
            raise Exception("Failed to locate separator")
        self.root = root.decode("string_escape").decode("utf-8")
        self.mountpoint = mountpoint.decode("string_escape").decode("utf-8")

    def mountpoint_tokens(self):
        return MountInfo.split_path(self.mountpoint)

    def __str__(self):
        return u"<Mount: {0} on {1}>".format(self.fstype, self.mountpoint).encode("utf8")

    def __unicode__(self):
        return u"<Mount: {0} on {1}>".format(self.fstype, self.mountpoint)

class MountInfo:
    def __init__(self):
        with open("/proc/self/mountinfo") as mountinfo:
            self.mounts = [ Mount(line) for line in mountinfo ]

    @staticmethod
    def _generate_common_prefix(path_tokens1, path_tokens2):
        for (token1, token2) in zip(path_tokens1, path_tokens2):
            if token1 == token2:
                yield token1
            else:
                break

    @staticmethod
    def _common_prefix_tokens(tokens1, tokens2):
        return list(MountInfo._generate_common_prefix(tokens1, tokens2))

    @staticmethod
    def split_path(path):
        tokens = []
        (dirname, basename) = os.path.split(path)
        while basename:
            tokens.append(basename)
            path = dirname
            (dirname, basename) = os.path.split(path)
        tokens.append(dirname)
        tokens.reverse()
        return tokens

    def _generate_mounts_beyond(self, path):
        pathtokens = MountInfo.split_path(path)
        for mount in self.mounts:
            common = MountInfo._common_prefix_tokens(mount.mountpoint_tokens(), pathtokens)
            if common == mount.mountpoint_tokens():
                yield mount
   
    def get_mount(self, path):
        path = os.path.abspath(path)
        mounts = list()
        most_specific = sorted(
            self._generate_mounts_beyond(path),
            lambda a,b: cmp(len(a.mountpoint_tokens()), len(b.mountpoint_tokens()))
        )[-1]
        return most_specific

    def get_fs(self, path):
        return self.get_mount(path).fstype

if __name__ == "__main__":
    mi = MountInfo()
    print(mi.get_fs(sys.argv[1]))
