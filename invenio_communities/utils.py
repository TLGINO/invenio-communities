# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2013, 2015, 2016 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Utils for communities."""

import os
import types
from functools import wraps
from math import ceil
from uuid import UUID

from flask import _request_ctx_stack, current_app, request
from invenio_db import db
from invenio_files_rest.errors import FilesException
from invenio_files_rest.models import Bucket, Location, ObjectVersion


class Pagination(object):
    """Helps with rendering pagination list."""

    def __init__(self, page, per_page, total_count):
        """Init pagination."""
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        """Return number of pages."""
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        """Return true if it has previous page."""
        return self.page > 1

    @property
    def has_next(self):
        """Return true if it has next page."""
        return self.page < self.pages

    def iter_pages(self, left_edge=1, left_current=1, right_current=3,
                   right_edge=1):
        """Iterate the pages."""
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


def render_template_to_string(input, _from_string=False, **context):
    """Render a template from the template folder with the given context.

    Code based on
    `<https://github.com/mitsuhiko/flask/blob/master/flask/templating.py>`_
    :param input: the string template, or name of the template to be
                  rendered, or an iterable with template names
                  the first one existing will be rendered
    :param context: the variables that should be available in the
                    context of the template.
    :return: a string
    """
    ctx = _request_ctx_stack.top
    ctx.app.update_template_context(context)
    if _from_string:
        template = ctx.app.jinja_env.from_string(input)
    else:
        template = ctx.app.jinja_env.get_or_select_template(input)
    return template.render(context)


def save_and_validate_logo(logo_stream, logo_filename, community_id):
    """Validate if communities logo is in limit size and save it."""
    cfg = current_app.config

    logos_bucket_id = cfg['COMMUNITIES_BUCKET_UUID']
    logos_bucket = Bucket.query.get(logos_bucket_id)
    ext = os.path.splitext(logo_filename)[1]
    ext = ext[1:] if ext.startswith('.') else ext

    if ext in cfg['COMMUNITIES_LOGO_EXTENSIONS']:
        key = "{0}/logo.{1}".format(community_id, ext)
        ObjectVersion.create(logos_bucket, key, stream=logo_stream)
        return ext
    else:
        return None


def get_oaiset_spec(community_id):
    """Return the OAISet 'spec' name for given community.

    :param community_id: ID of the community.
    :type community_id: str
    :returns: Formatted OAISet ID ('spec').
    :rtype: str
    """
    return current_app.config['COMMUNITIES_OAI_FORMAT'].format(
        community_id=community_id)


def initialize_communities_bucket():
    """Initialize the communities file bucket.

    :raises: `invenio_files_rest.errors.FilesException`
    """
    bucket_id = UUID(current_app.config['COMMUNITIES_BUCKET_UUID'])

    if Bucket.query.get(bucket_id):
        raise FilesException("Bucket with UUID {} already exists.".format(
            bucket_id))
    else:
        storage_class = current_app.config['FILES_REST_DEFAULT_STORAGE_CLASS']
        location = Location.get_default()
        bucket = Bucket(id=bucket_id,
                        location=location,
                        default_storage_class=storage_class)
        db.session.add(bucket)
        db.session.commit()
