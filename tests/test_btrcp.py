
import pytest
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import btrcp
import runtestutils






def test_test():
    _mk_disk_image(Path('test.img'))

def test_failed():
    assert 1 == 2

def test_OK():
    assert 1 == 1

