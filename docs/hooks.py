import logging
import os
import shutil
from distutils.dir_util import copy_tree

logger = logging.getLogger("mkdocs")


def copy_get(config, **kwargs):
    site_dir = config["site_dir"]
    logger.info("Copying logo from hook")
    copy_tree("../logo/", os.path.join(site_dir, "logo"))
