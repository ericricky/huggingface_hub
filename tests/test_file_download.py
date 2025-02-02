# Copyright 2020 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import requests
from huggingface_hub.constants import (
    CONFIG_NAME,
    PYTORCH_WEIGHTS_NAME,
    REPO_TYPE_DATASET,
)
from huggingface_hub.file_download import cached_download, filename_to_url, hf_hub_url

from .testing_utils import (
    DUMMY_UNKWOWN_IDENTIFIER,
    SAMPLE_DATASET_IDENTIFIER,
    OfflineSimulationMode,
    offline,
)


MODEL_ID = DUMMY_UNKWOWN_IDENTIFIER
# An actual model hosted on huggingface.co

DATASET_ID = SAMPLE_DATASET_IDENTIFIER
# An actual dataset hosted on huggingface.co


REVISION_ID_DEFAULT = "main"
# Default branch name
REVISION_ID_ONE_SPECIFIC_COMMIT = "f2c752cfc5c0ab6f4bdec59acea69eefbee381c2"
# One particular commit (not the top of `main`)
REVISION_ID_INVALID = "aaaaaaa"
# This commit does not exist, so we should 404.

PINNED_SHA1 = "d9e9f15bc825e4b2c9249e9578f884bbcb5e3684"
# Sha-1 of config.json on the top of `main`, for checking purposes
PINNED_SHA256 = "4b243c475af8d0a7754e87d7d096c92e5199ec2fe168a2ee7998e3b8e9bcb1d3"
# Sha-256 of pytorch_model.bin on the top of `main`, for checking purposes

DATASET_REVISION_ID_ONE_SPECIFIC_COMMIT = "e25d55a1c4933f987c46cc75d8ffadd67f257c61"
# One particular commit for DATASET_ID
DATASET_SAMPLE_PY_FILE = "custom_squad.py"


class CachedDownloadTests(unittest.TestCase):
    def test_bogus_url(self):
        url = "https://bogus"
        with self.assertRaisesRegex(ValueError, "Connection error"):
            _ = cached_download(url)

    def test_no_connection(self):
        invalid_url = hf_hub_url(
            MODEL_ID, filename=CONFIG_NAME, revision=REVISION_ID_INVALID
        )
        valid_url = hf_hub_url(
            MODEL_ID, filename=CONFIG_NAME, revision=REVISION_ID_DEFAULT
        )
        self.assertIsNotNone(cached_download(valid_url, force_download=True))
        for offline_mode in OfflineSimulationMode:
            with offline(mode=offline_mode):
                with self.assertRaisesRegex(ValueError, "Connection error"):
                    _ = cached_download(invalid_url)
                with self.assertRaisesRegex(ValueError, "Connection error"):
                    _ = cached_download(valid_url, force_download=True)
                self.assertIsNotNone(cached_download(valid_url))

    def test_file_not_found(self):
        # Valid revision (None) but missing file.
        url = hf_hub_url(MODEL_ID, filename="missing.bin")
        with self.assertRaisesRegex(requests.exceptions.HTTPError, "404 Client Error"):
            _ = cached_download(url)

    def test_revision_not_found(self):
        # Valid file but missing revision
        url = hf_hub_url(MODEL_ID, filename=CONFIG_NAME, revision=REVISION_ID_INVALID)
        with self.assertRaisesRegex(requests.exceptions.HTTPError, "404 Client Error"):
            _ = cached_download(url)

    def test_standard_object(self):
        url = hf_hub_url(MODEL_ID, filename=CONFIG_NAME, revision=REVISION_ID_DEFAULT)
        filepath = cached_download(url, force_download=True)
        metadata = filename_to_url(filepath)
        self.assertEqual(metadata, (url, f'"{PINNED_SHA1}"'))

    def test_standard_object_rev(self):
        # Same object, but different revision
        url = hf_hub_url(
            MODEL_ID, filename=CONFIG_NAME, revision=REVISION_ID_ONE_SPECIFIC_COMMIT
        )
        filepath = cached_download(url, force_download=True)
        metadata = filename_to_url(filepath)
        self.assertNotEqual(metadata[1], f'"{PINNED_SHA1}"')
        # Caution: check that the etag is *not* equal to the one from `test_standard_object`

    def test_lfs_object(self):
        url = hf_hub_url(
            MODEL_ID, filename=PYTORCH_WEIGHTS_NAME, revision=REVISION_ID_DEFAULT
        )
        filepath = cached_download(url, force_download=True)
        metadata = filename_to_url(filepath)
        self.assertEqual(metadata, (url, f'"{PINNED_SHA256}"'))

    def test_dataset_standard_object_rev(self):
        url = hf_hub_url(
            DATASET_ID,
            filename=DATASET_SAMPLE_PY_FILE,
            repo_type=REPO_TYPE_DATASET,
            revision=DATASET_REVISION_ID_ONE_SPECIFIC_COMMIT,
        )
        # We can also just get the same url by prefixing "datasets" to repo_id:
        url2 = hf_hub_url(
            repo_id=f"datasets/{DATASET_ID}",
            filename=DATASET_SAMPLE_PY_FILE,
            revision=DATASET_REVISION_ID_ONE_SPECIFIC_COMMIT,
        )
        self.assertEqual(url, url2)
        # now let's download
        filepath = cached_download(url, force_download=True)
        metadata = filename_to_url(filepath)
        self.assertNotEqual(metadata[1], f'"{PINNED_SHA1}"')

    def test_dataset_lfs_object(self):
        url = hf_hub_url(
            DATASET_ID,
            filename="dev-v1.1.json",
            repo_type=REPO_TYPE_DATASET,
            revision=DATASET_REVISION_ID_ONE_SPECIFIC_COMMIT,
        )
        filepath = cached_download(url, force_download=True)
        metadata = filename_to_url(filepath)
        self.assertEqual(
            metadata,
            (url, '"95aa6a52d5d6a735563366753ca50492a658031da74f301ac5238b03966972c9"'),
        )
