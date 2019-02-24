# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the LICENSE file in
# the root directory of this source tree. An additional grant of patent rights
# can be found in the PATENTS file in the same directory.

import torch

from . import FairseqDataset


class TransformEosDataset(FairseqDataset):
    """A :class:`~fairseq.data.FairseqDataset` wrapper that appends/prepends/strips EOS.

    Note that the transformation is applied in :func:`collater`.

    Args:
        dataset (~fairseq.data.FairseqDataset): dataset to wrap
        eos (int): index of the end-of-sentence symbol
        append_eos_to_src (bool, optional): append EOS to the end of src
        remove_eos_from_src (bool, optional): remove EOS from the end of src
        append_eos_to_tgt (bool, optional): append EOS to the end of tgt
        remove_eos_from_tgt (bool, optional): remove EOS from the end of tgt
    """

    def __init__(
        self,
        dataset,
        eos,
        append_eos_to_src=False,
        remove_eos_from_src=False,
        append_eos_to_tgt=False,
        remove_eos_from_tgt=False,
    ):
        if not isinstance(dataset, FairseqDataset):
            raise ValueError('dataset must be an instance of FairseqDataset')
        if append_eos_to_src and remove_eos_from_src:
            raise ValueError('cannot combine append_eos_to_src and remove_eos_from_src')
        if append_eos_to_tgt and remove_eos_from_tgt:
            raise ValueError('cannot combine append_eos_to_tgt and remove_eos_from_tgt')

        self.dataset = dataset
        self.eos = torch.LongTensor([eos])
        self.append_eos_to_src = append_eos_to_src
        self.remove_eos_from_src = remove_eos_from_src
        self.append_eos_to_tgt = append_eos_to_tgt
        self.remove_eos_from_tgt = remove_eos_from_tgt

        # precompute how we should adjust the reported sizes
        self._src_delta = 0
        self._src_delta += 1 if append_eos_to_src else 0
        self._src_delta -= 1 if remove_eos_from_src else 0
        self._tgt_delta = 0
        self._tgt_delta += 1 if append_eos_to_tgt else 0
        self._tgt_delta -= 1 if remove_eos_from_tgt else 0

        self._checked_src = False
        self._checked_tgt = False

    def _check_src(self, src, expect_eos):
        if not self._checked_src:
            assert (src[-1] == self.eos[0]) == expect_eos
            self._checked_src = True

    def _check_tgt(self, tgt, expect_eos):
        if not self._checked_tgt:
            assert (tgt[-1] == self.eos[0]) == expect_eos
            self._checked_tgt = True

    def __getitem__(self, index):
        return self.dataset[index]

    def __len__(self):
        return len(self.dataset)

    def collater(self, samples):

        def transform(item):
            if self.append_eos_to_src:
                self._check_src(item['source'], expect_eos=False)
                item['source'] = torch.cat([item['source'], self.eos])
            if self.remove_eos_from_src:
                self._check_src(item['source'], expect_eos=True)
                item['source'] = item['source'][:-1]
            if self.append_eos_to_tgt:
                self._check_tgt(item['target'], expect_eos=False)
                item['target'] = torch.cat([item['target'], self.eos])
            if self.remove_eos_from_tgt:
                self._check_tgt(item['target'], expect_eos=True)
                item['target'] = item['target'][:-1]
            return item

        samples = list(map(transform, samples))
        return self.dataset.collater(samples)

    def get_dummy_batch(self, *args, **kwargs):
        return self.dataset.get_dummy_batch(*args, **kwargs)

    def num_tokens(self, index):
        return self.dataset.num_tokens(index)

    def size(self, index):
        src_len, tgt_len = self.dataset.size(index)
        return (src_len + self._src_delta, tgt_len + self._tgt_delta)

    def ordered_indices(self):
        # NOTE: we assume that the ordering does not change based on the
        # addition or removal of eos
        return self.dataset.ordered_indices()

    @property
    def supports_prefetch(self):
        return getattr(self.dataset, 'supports_prefetch', False)

    def prefetch(self, indices):
        return self.dataset.prefetch(indices)