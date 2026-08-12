import logging
import os
from distutils.dir_util import copy_tree

logger = logging.getLogger("mkdocs")


def patch_pygments_filename(config, **kwargs):
    """Work around pymdownx+pygments crash when highlight title is None.

    pymdownx passes ``filename=title`` into Pygments; with ``auto_title: false``
    that is ``None``, and Pygments 2.20 calls ``html.escape(None)``.
    """
    from pymdownx.highlight import Highlight

    if getattr(Highlight.highlight, "_clak_none_title_patched", False):
        return config

    original = Highlight.highlight

    def _highlight(
        self,
        src,
        language,
        css_class="highlight",
        hl_lines=None,
        linestart=-1,
        linestep=-1,
        linespecial=-1,
        inline=False,
        classes=None,
        id_value="",
        attrs=None,
        title=None,
        code_block_count=0,
    ):
        if title is None:
            title = ""
        return original(
            self,
            src,
            language,
            css_class=css_class,
            hl_lines=hl_lines,
            linestart=linestart,
            linestep=linestep,
            linespecial=linespecial,
            inline=inline,
            classes=classes,
            id_value=id_value,
            attrs=attrs,
            title=title,
            code_block_count=code_block_count,
        )

    _highlight._clak_none_title_patched = True
    Highlight.highlight = _highlight
    logger.info("Patched pymdownx highlight for None title/filename")
    return config


def copy_get(config, **kwargs):
    site_dir = config["site_dir"]
    logger.info("Copying logo from hook")
    copy_tree("../logo/", os.path.join(site_dir, "logo"))
