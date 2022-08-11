from __future__ import annotations
from pathlib import Path
from logging import getLogger, Logger
from fileinput import hook_compressed
from dataclasses import dataclass, field, fields
from typing import Iterator, get_type_hints, Generator

import numpy as np
import numpy.typing as npt
from pysam import TabixFile

from .data import Data
from .genotypes import GenotypesRefAlt


@dataclass
class Extra:
    """
    An extra field on a line in the .hap file

    Attributes
    ----------
    name: str
        The name of the extra field
    fmt: str = "s"
        The python fmt string of the field value; indicates how to format the value
    description: str = ""
        A description of the extra field
    """

    name: str
    fmt: str = "s"
    description: str = ""
    _type: type = field(init=False, repr=False)

    def __post_init(self):
        if self.fmt.endswith("s"):
            self._type = str
        elif self.fmt.endswith("d"):
            self._type = int
        elif self.fmt.endswith("f"):
            self._type = float
        else:
            raise ValueError("Unsupported extra type '{}'!".format(self.fmt[-1]))

    @classmethod
    def from_hap_spec(cls, line: str) -> Extra:
        """
        Convert an "extra" line in the header of a .hap file into an Extra object

        Parameters
        ----------
        line: str
            An "extra" field, as it appears declared in the header

        Returns
        -------
        Extra
            An Extra object
        """
        line = line[3:].split("\t")
        return cls(name=line[0], fmt=line[1], description=line[2])

    def to_hap_spec(self, line_type_symbol: str) -> str:
        """
        Convert an Extra object into a header line in the .hap format spec

        Parameters
        ----------
        hap_id: str
            The ID of the haplotype associated with this variant

        Returns
        -------
        str
            A valid variant line (V) in the .hap format spec
        """
        return (
            "#"
            + line_type_symbol
            + "\t"
            + "\t".join((self.name, self.fmt, self.description))
        )

    @property
    def fmt_str(self) -> str:
        """
        Convert an Extra into a fmt string

        Returns
        -------
        str
            A python format string (ex: "{beta:.3f}")
        """
        return "{" + self.name + ":" + self.fmt + "}"


class classproperty(object):
    """
    A daad-simple read-only decorator that combines the functionality of
    @classmethod and @property

    Stolen from https://stackoverflow.com/a/13624858/16815703
    """

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


# We declare this class to be a dataclass to automatically define __init__ and a few
# other methods.
@dataclass
class Variant:
    """
    A variant within the .hap format spec

    In order to use this class with the Haplotypes class, you should
    1) add properties to the class for each of extra fields
    2) override the _extras property to describe the header declaration

    Attributes
    ----------
    start: int
        The chromosomal start position of the variant
    end: int
        The chromosomal end position of the variant

        In most cases this will be the same as the start position
    id: str
        The variant's unique ID
    allele: str
        The allele of this variant within the Haplotype
    _extras: tuple[Extra]
        Extra fields for the haplotype

    Examples
    --------
    Let's extend this class and add an extra field called "score"

    >>> from dataclasses import dataclass, field
    >>> @dataclass
    >>> class CustomVariant(Variant):
    ...     score: float
    ...     _extras: tuple = field(
    ...         repr=False,
    ...         init=False,
    ...         default = (
    ...             Extra("score", ".3f", "Importance of inclusion"),
    ...         ),
    ...     )
    """

    start: int
    end: int
    id: str
    allele: str
    _extras: tuple = field(default=tuple(), init=False, repr=False)

    @property
    def ID(self):
        """
        Create an alias for the id property
        """
        return self.id

    @property
    # TODO: use @cached_property in py3.8
    def _fmt(self):
        extras = ""
        if len(self._extras):
            extras = "\t" + "\t".join(extra.fmt_str for extra in self._extras)
        return "V\t{hap:s}\t{start:d}\t{end:d}\t{id:s}\t{allele:s}" + extras

    @classproperty
    # TODO: use @cached_property in py3.8
    def types(cls) -> dict[str, type]:
        """
        Obtain the types of each property in the object

        Returns
        -------
        dict[str, type]
            A mapping of each property in the object to its type
        """
        return {k: v for k, v in get_type_hints(cls).items() if not k.startswith("_")}

    @classmethod
    def from_hap_spec(
        cls: Variant,
        line: str,
        types: dict[str, type] = None,
    ) -> tuple[str, Variant]:
        """
        Convert a variant line into a Variant object in the .hap format spec

        Note that this implementation does NOT support having more extra fields than
        appear in the header

        Parameters
        ----------
        line: str
            A variant (V) line from the .hap file
        types: dict[str, type], optional
            The order of the extra fields if different from the order in _extras

        Returns
        -------
        tuple[str, Variant]
            The haplotype ID and Variant object for the variant
        """
        assert line[0] == "V", "Attempting to init a Variant with a non-V line"
        line = line[2:].split("\t")
        hap_id = line[0]
        line = line[1:]
        types = types or cls.types
        var_fields = {
            name: val(line[idx]) for idx, (name, val) in enumerate(types.items())
        }
        return hap_id, cls(**var_fields)

    def to_hap_spec(self, hap_id: str) -> str:
        """
        Convert a Variant object into a variant line in the .hap format spec

        Parameters
        ----------
        hap_id: str
            The ID of the haplotype associated with this variant

        Returns
        -------
        str
            A valid variant line (V) in the .hap format spec
        """
        return self._fmt.format(**self.__dict__, hap=hap_id)

    @classmethod
    def extras_head(cls) -> set:
        """
        Return the header lines of the extra fields that are supported

        Returns
        -------
        tuple
            The header lines of the extra fields
        """
        return set(extra.to_hap_spec("V") for extra in cls._extras)

    @classmethod
    def extras_order(cls) -> tuple[str]:
        """
        The names of the extra fields in order

        Returns
        -------
        tuple[str]
            The names of the extra fields in the order in which they are stored
        """
        return tuple(extra.name for extra in cls._extras)


# We declare this class to be a dataclass to automatically define __init__ and a few
# other methods.
@dataclass
class Haplotype:
    """
    A haplotype within the .hap format spec

    In order to use this class with the Haplotypes class, you should
    1) add properties to the class for each of extra fields
    2) override the _extras property to describe the header declaration

    Attributes
    ----------
    chrom: str
        The contig to which this haplotype belongs
    start: int
        The chromosomal start position of the haplotype
    end: int
        The chromosomal end position of the haplotype
    id: str
        The haplotype's unique ID
    variants: tuple[Variant]
        The variants in this haplotype
    _extras: tuple[Extra]
        Extra fields for the haplotype

    Examples
    --------
    Let's extend this class and add an extra field called "ancestry"

    >>> from dataclasses import dataclass, field
    >>> @dataclass
    >>> class CustomHaplotype(Haplotype):
    ...     ancestry: str
    ...     _extras: tuple = field(
    ...         repr=False,
    ...         init=False,
    ...         default = (
    ...             Extra("ancestry", "s", "Local ancestry"),
    ...         ),
    ...     )
    """

    chrom: str
    start: int
    end: int
    id: str
    variants: tuple = field(default_factory=tuple, init=False)
    _extras: tuple = field(default=tuple(), init=False, repr=False)

    @property
    def ID(self):
        """
        Create an alias for the id property
        """
        return self.id

    @property
    # TODO: use @cached_property in py3.8
    def _fmt(self):
        extras = ""
        if len(self._extras):
            extras = "\t" + "\t".join(extra.fmt_str for extra in self._extras)
        return "H\t{chrom:s}\t{start:d}\t{end:d}\t{id:s}" + extras

    @property
    # TODO: use @cached_property in py3.8
    def varIDs(self):
        return tuple(var.id for var in self.variants)

    @classproperty
    # TODO: use @cached_property in py3.8
    def types(cls) -> dict[str, type]:
        """
        Obtain the types of each property in the object

        Returns
        -------
        dict[str, type]
            A mapping of each property in the object to its type
        """
        return {
            k: v
            for k, v in get_type_hints(cls).items()
            if not (k.startswith("_") or k == "variants")
        }

    @classmethod
    def from_hap_spec(
        cls: Haplotype,
        line: str,
        variants: tuple[Variant] = tuple(),
        types: dict[str, type] = None,
    ) -> Haplotype:
        """
        Convert a variant line into a Haplotype object in the .hap format spec

        Note that this implementation does NOT support having more extra fields than
        appear in the header

        Parameters
        ----------
        line: str
            A variant (H) line from the .hap file
        variants: tuple[Variant], optional
            The Variants in this haplotype
        types: dict[str, type], optional
            The types of each property in the object

        Returns
        -------
        Haplotype
            The Haplotype object for the variant
        """
        assert line[0] == "H", "Attempting to init a Haplotype with a non-H line"
        line = line[2:].split("\t")
        types = types or cls.types
        hap_fields = {
            name: val(line[idx]) for idx, (name, val) in enumerate(types.items())
        }
        hap = cls(**hap_fields)
        hap.variants = variants
        return hap

    def to_hap_spec(self) -> str:
        """
        Convert a Haplotype object into a haplotype line in the .hap format spec

        Returns
        -------
        str
            A valid haplotype line (H) in the .hap format spec
        """
        return self._fmt.format(**self.__dict__)

    @classmethod
    def extras_head(cls) -> set:
        """
        Return the header lines of the extra fields that are supported

        Returns
        -------
        tuple
            The header lines of the extra fields
        """
        return set(extra.to_hap_spec("H") for extra in cls._extras)

    @classmethod
    def extras_order(cls) -> tuple[str]:
        """
        The names of the extra fields in order

        Returns
        -------
        tuple[str]
            The names of the extra fields in the order in which they are stored
        """
        return tuple(extra.name for extra in cls._extras)

    def transform(self, genotypes: GenotypesRefAlt) -> npt.NDArray[bool]:
        """
        Transform a genotypes matrix via the current haplotype

        Each entry in the returned matrix denotes the presence of the current haplotype
        in each chromosome of each sample in the Genotypes object

        Parameters
        ----------
        genotypes : GenotypesRefAlt
            The genotypes which to transform using the current haplotype

            If the genotypes have not been loaded into the Genotypes object yet, this
            method will call Genotypes.read(), while loading only the needed variants

        Returns
        -------
        npt.NDArray[bool]
            A 2D matrix of shape (num_samples, 2) where each entry in the matrix
            denotes the presence of the haplotype in one chromosome of a sample
        """
        var_IDs = self.varIDs
        gts = genotypes.subset(variants=var_IDs)
        # check: were any of the variants absent from the genotypes?
        if len(gts.variants) < len(var_IDs):
            missing_IDs = set(var_IDs) - set(gts.variants["id"])
            raise ValueError(
                f"Variants {missing_IDs} are present in haplotype '{self.id}' but "
                "absent in the provided genotypes"
            )
        # create a np array denoting the alleles that we want
        # note: the excessive use of square-brackets gives us shape (1, n, 1)
        allele_arr = np.array(
            [
                [
                    [int(var.allele != gts.variants[i]["ref"])]
                    for i, var in enumerate(self.variants)
                ]
            ]
        )
        # look for the presence of each allele in each chromosomal strand
        # and then just AND them together
        return np.all(allele_arr == gts.data, axis=1)


class Haplotypes(Data):
    """
    A class for processing haplotypes from a file

    Attributes
    ----------
    fname: Path | str
        The path to the file containing the data
    data: dict[str, Haplotype]
        A dict of Haplotype objects keyed by their IDs
    types: dict
        A dict of class names keyed by the symbol denoting their line type

        Ex: {'H': Haplotype, 'V': Variant}
    version: str
        A string denoting the current file format version
    log: Logger
        A logging instance for recording debug statements.

    Examples
    --------
    Parsing a basic .hap file without any extra fields is simple:
    >>> haplotypes = Haplotypes.load('tests/data/basic.hap')
    >>> haps = haplotypes.data # a dictionary of Haplotype objects

    If the .hap file contains extra fields, you'll need to call the read() method
    manually. You'll also need to create Haplotype and Variant subclasses that support
    the extra fields and then specify the names of the classes when you initialize the
    Haplotypes object:
    >>> haplotypes = Haplotypes('tests/data/simphenotype.hap', HaptoolsHaplotype)
    >>> haplotypes.read()
    >>> haps = haplotypes.data # a dictionary of Haplotype objects
    """

    def __init__(
        self,
        fname: Path | str,
        haplotype: type[Haplotype] = Haplotype,
        variant: type[Variant] = Variant,
        log: Logger = None,
    ):
        super().__init__(fname, log)
        self.data = None
        # note: it's important that self.types is created such that its keys are sorted
        # otherwise, the write() method might create unsorted files
        self.types = {"H": haplotype, "V": variant}
        self.version = "0.1.0"

    @classmethod
    def load(
        cls: Haplotypes,
        fname: Path | str,
        region: str = None,
        haplotypes: set[str] = None,
    ) -> Haplotypes:
        """
        Load haplotypes from a .hap file

        Read the file contents

        Parameters
        ----------
        fname: Path
            See documentation for :py:attr:`~.Data.fname`
        region: str, optional
            See documentation for :py:meth:`~.Haplotypes.read`
        haplotypes: set[str], optional
            See documentation for :py:meth:`~.Haplotypes.read`

        Returns
        -------
        Haplotypes
            A Haplotypes object with the data loaded into its properties
        """
        haps = cls(fname)
        haps.read(region, haplotypes)
        return haps

    def check_header(
        self,
        lines: list[str],
        check_version=True,
        softly=False,
    ) -> tuple[dict, dict[str, tuple[Extra]]]:
        """
        1) Check and parse any metadata and 2) check that any extra fields declared in
        the .haps file can be handled by the Variant and Haplotype classes
        provided in __init__()

        This function is called automatically by other methods that read .hap files

        Parameters
        ----------
        lines: list[str]
            Header lines from the .hap file. Any lines beginning with # may appear
            in this list, especially if the file is sorted. So this may include regular
            comments, too.
        check_version: bool, optional
            Whether to also check the version of the file
        softly: bool, optional
            If True, then this function will not raise any ValueErrors. Instead, it
            will only issue errors via the logging module, which may be ignored.

        Raises
        ------
        ValueError
            If any of the header lines are not supported

        Returns
        -------
        tuple[dict, dict[str, tuple[Extra]]]
            The metadata for the file, contained within the header lines and encoded as
            a dictionary where the names are keys and any subsequent fields are values

            The second dictionary encodes the set of declared Extras for each line type
        """
        # first, set the error messenger depending on the softly parameter
        if softly:

            def err_msgr(msg):
                self.log.error(msg)

        else:

            def err_msgr(msg):
                raise ValueError(msg)

        # init metadata dict, extra dict, and expected extra fields
        metas = {}
        extras = {line_t: [] for line_t, line_type in self.types.items()}
        exp_extras = {
            line_t: {line for line in line_type.extras_head()}
            for line_t, line_type in self.types.items()
        }
        self.log.info("Checking header")
        for line in lines:
            # the line could be either a metadata line, an extra-field declaration, or
            # a humble comment. (In the latter case, we just ignore it)
            if line[2] == "\t" and line[1] in self.types.keys():
                # try to parse the extra line and store it for later
                try:
                    extras[line[1]].append(Extra.from_hap_spec(line))
                except:
                    # if we can't parse, we just assume this was a comment
                    self.log.debug(
                        f"Line '{line}' looks like an extra field declaration, but "
                        "failed to parse as one. Ignoring for now."
                    )
                    continue
                # now, let's check that this field was expected
                name = extras[line[1]][-1].name
                try:
                    exp_extras[line[1]].remove(line)
                except KeyError:
                    err_msgr(
                        f"The extra field '{name}' is declared in the header of the"
                        " .hap file but is not accepted by this tool."
                    )
            elif line[1] == "\t":
                met = line[2:].split("\t")
                if check_version and met[0] == "version":
                    self.log.debug("Checking .hap format spec version")
                    if met[1] != self.version:
                        # the observed and expected major, minor, and patch versions
                        o_major, o_minor, o_patch = map(int, met[1].split("."))
                        e_major, e_minor, e_patch = map(int, self.version.split("."))
                        if o_major != e_major or o_minor > e_minor:
                            err_msgr(
                                f"The version of the provided .hap file is v{met[1]} "
                                f"but this tool only works with >= v{e_major}.0.x and "
                                f"<= v{e_major}.{e_minor}.x .hap files"
                            )
                        elif o_minor < e_minor:
                            self.log.warning(
                                f"The version of the provided .hap file, v{met[1]}, "
                                f"is outdated. Consider upgrading to v{self.version}"
                            )
                        elif o_patch < e_patch:
                            self.log.warning("There have been fixes to the .hap spec")
                    metas["version"] = met[1]
                elif met[0] in ["order" + t for t in self.types.keys()]:
                    self.log.debug(
                        f"Storing {met[0][-1]} extra fields in order {*met[1:],}"
                    )
                    metas.setdefault("order", {})[met[0][5:]] = tuple(met[1:])
                else:
                    self.log.debug(
                        f"Line '{line}' looks like a metadata line but we could't "
                        "recognize the metadata name. Ignoring for now."
                    )
        # if there are any fields left...
        if any(exp_extras.values()):
            names = [line.split("\t", maxsplit=2)[1] for line in exp_extras]
            error_msgr(
                "Expected the input .hap file to have these extra fields, but they "
                f"don't seem to be declared in the header: {*names,}"
            )
        return metas, extras

    def _line_type(self, line: str) -> type:
        """
        Return the type of line that this line matches

        Parameters
        ----------
        line: str
            A line of the .hap file

        Returns
        -------
        type
            The name of the class corresponding with the type of this line
        """
        line_types = self.types.keys()
        if line[0] in line_types:
            return line[0]
        else:
            # if none of the lines matched, return None
            return None

    def read(self, region: str = None, haplotypes: set[str] = None):
        """
        Read haplotypes from a .hap file into a list stored in :py:attr:`~.Haplotypes.data`

        Parameters
        ----------
        region: str, optional
            The region from which to extract haplotypes; ex: 'chr1:1234-34566' or 'chr7'

            For this to work, the .hap file must be indexed and the seqname must match!

            Defaults to loading all haplotypes
        haplotypes: set[str], optional
            A list of haplotype IDs corresponding to a subset of the haplotypes to
            extract

            Defaults to loading haplotypes from all samples
        """
        super().read()
        self.data = {}
        var_haps = {}
        for line in self.__iter__(region, haplotypes):
            if isinstance(line, Haplotype):
                self.data[line.id] = line
            elif isinstance(line, Variant):
                hap_id = line.hap
                del line.hap
                # store the variant for later
                var_haps.setdefault(hap_id, []).append(line)
        for hap in var_haps:
            self.data[hap].variants = tuple(var_haps[hap])
        self.log.info(f"Loaded {len(self.data)} haplotypes from .hap file")

    def _get_field_types(
        self,
        extras: dict[str, tuple[Extra]],
        order: dict[str, tuple] = None,
    ) -> dict[str, dict[str.type]]:
        """
        Get the types of each field in a line, for each line type

        This is a helper function for __iter__()

        Parameters
        ----------
        extras: dict[str, tuple[Extra]]
            For each line type (as the keys), what kinds of extra fields were declared?
        order: dict[str, tuple], optional
            For each line type (as the keys), what is the ordering of the extra fields?

        Returns
        -------
        dict[str, dict[str, type]]
            For each line type (as the keys), return a dict mapping each extra field
            name to its type (ex: str, int, float, etc)

            The items are returned in the order that they appear in either the extras
            or order parameters
        """
        types = {}
        for symbol, line_type in self.types.items():
            types[symbol] = line_type.types
            if order is not None and symbol in order:
                extras_order = order[symbol]
            else:
                extras_order = tuple(extra.name for extra in extras[symbol])
            for extra in extras_order:
                # remove the extra from types[symbol] and then add it back in again
                # so that the extras appear in the same order as extras_order
                types[symbol][extra] = types[symbol].pop(extra)
        return types

    def __iter__(
        self, region: str = None, haplotypes: set[str] = None
    ) -> Iterator[Variant | Haplotype]:
        """
        Read haplotypes from a .hap file line by line without storing anything

        Parameters
        ----------
        region: str, optional
            The region from which to extract haplotypes; ex: 'chr1:1234-34566' or 'chr7'

            For this to work, the .hap file must be indexed and the seqname must match!

            Defaults to loading all haplotypes
        haplotypes: set[str], optional
            A list of haplotype IDs corresponding to a subset of the haplotypes to
            extract

            Defaults to loading haplotypes from all samples

        Yields
        ------
        Iterator[Variant|Haplotype]
            An iterator over each line in the file, where each line is encoded as a
            Variant or Haplotype containing each of the class properties

        Examples
        --------
        If you're worried that the contents of the .hap file will be large, you may
        opt to parse the file line-by-line instead of loading it all into memory at
        once. In cases like these, you can use the __iter__() method in a for-loop:
        >>> haplotypes = Haplotypes('tests/data/basic.hap')
        >>> for line in haplotypes:
        ...     print(line)

        Call the function manually to pass it the region or haplotypes params:
        >>> haplotypes = Haplotypes('tests/data/basic.hap.gz')
        >>> for line in haplotypes.__iter__(
        ...    region='21:26928472-26941960', haplotypes={"chr21.q.3365*1"}
        ... ):
        ...     print(line)
        """
        # if the user requested a specific region, then we should handle it using tabix
        # else, we use a regular text opener
        if region:
            haps_file = TabixFile(str(self.fname))
            metas, extras = self.check_header(list(haps_file.header))
            types = self._get_field_types(extras, metas.get("order"))
            if region:
                region_positions = region.split(":", maxsplit=1)[1]
                # fetch region
                # we already know that each line will start with an H, so we don't
                # need to check that
                for line in haps_file.fetch(region):
                    hap = self.types["H"].from_hap_spec(line, types=types["H"])
                    if haplotypes is not None:
                        if hap.id not in haplotypes:
                            continue
                        haplotypes.remove(hap.id)
                    yield hap
            else:
                for line in haps_file.fetch():
                    # we only want lines that start with an H
                    line_type = self._line_type(line)
                    if line_type == "H":
                        hap = self.types["H"].from_hap_spec(line, types=types["H"])
                        if hap.id in haplotypes:
                            yield hap
                            haplotypes.remove(hap.id)
                    elif line_type > "H":
                        # if we've already passed all of the H's, we can just exit
                        # We assume the file has been sorted so that all of the H lines
                        # come before the V lines
                        break
            # query for the variants of each haplotype
            for hap_id in self.data:
                # exclude variants outside the desired region
                hap_region = hap_id
                if region:
                    hap_region = hap_id + ":" + region_positions
                # fetch region
                # we already know that each line will start with a V, so we don't
                # need to check that
                for line in haps_file.fetch(hap_region):
                    line_type = self._line_type(line)
                    if line_type == "V":
                        var = self.types["V"].from_hap_spec(line, types=types["V"])[1]
                        # add the haplotype, since otherwise, the user won't know
                        # which haplotype this variant belongs to
                        var.hap = hap_id
                        yield var
                    else:
                        self.log.warning(
                            "Check that chromosomes are distinct from your hap IDs!"
                        )
            haps_file.close()
        else:
            # the file is not indexed, so we can't assume it's sorted, either
            # use hook_compressed to automatically handle gz files
            with hook_compressed(self.fname, mode="rt") as haps:
                self.log.info("Not taking advantage of indexing.")
                header_lines = []
                for line in haps:
                    line = line.rstrip("\n")
                    line_type = self._line_type(line)
                    if line[0] == "#":
                        # store header for later
                        try:
                            header_lines.append(line)
                        except AttributeError:
                            # this happens when we encounter a line beginning with a #
                            # after already having seen a valid line type (like H or V)
                            # These are usually just comment lines, so we can ignore it
                            pass
                    else:
                        if header_lines:
                            metas, extras = self.check_header(header_lines)
                            types = self._get_field_types(extras, metas.get("order"))
                            header_lines = None
                            self.log.info("Finished reading header.")
                        if line_type == "H":
                            temp_hap = self.types["H"].from_hap_spec(
                                line, types=types["H"]
                            )
                            if haplotypes is None or temp_hap.id in haplotypes:
                                yield temp_hap
                        elif line_type == "V":
                            hap_id, var = self.types["V"].from_hap_spec(
                                line, types=types["V"]
                            )
                            if haplotypes is None or hap_id in haplotypes:
                                # add the haplotype, since otherwise, the user won't
                                # know which haplotype this variant belongs to
                                var.hap = hap_id
                                yield var
                        else:
                            self.log.warning(
                                f"Ignoring unsupported line type '{line[0]}'"
                            )

    def to_str(self) -> Generator[str, None, None]:
        """
        Create a string representation of this Haplotype

        Yields
        ------
        Generator[str, None, None]
            A list of lines (strings) to include in the output
        """
        for symbol, line_instance in self.types.items():
            extras_order = line_instance.extras_order()
            if extras_order:
                yield f"#\torder{symbol}\t" + "\t".join(line_instance.extras_order())
        yield "#\tversion\t" + self.version
        for line_instance in self.types.values():
            yield from sorted(line_instance.extras_head())
        for hap in self.data.values():
            yield self.types["H"].to_hap_spec(hap)
        for hap in self.data.values():
            for var in hap.variants:
                yield self.types["V"].to_hap_spec(var, hap.id)

    def __repr__(self):
        return "\n".join(self.to_str())

    def write(self):
        """
        Write the contents of this Haplotypes object to the file at
        :py:attr:`~.Haplotypes.fname`

        If the items in :py:attr:`~.Haplotypes.data` are sorted, the output should be
        automatically sorted such that "sort -k1,4" would leave the output unchanged

        Examples
        --------
        To write to a .hap file, you must first initialize a Haplotypes object and then
        fill out the data property:
        >>> haplotypes = Haplotypes('tests/data/basic.hap')
        >>> haplotypes.data = {'H1': Haplotype('chr1', 0, 10, 'H1')}
        >>> haplotypes.write()
        """
        with hook_compressed(self.fname, mode="wt") as haps:
            for line in self.to_str():
                haps.write(line + "\n")

    def transform(
        self,
        genotypes: GenotypesRefAlt,
        hap_gts: GenotypesRefAlt = None,
    ) -> GenotypesRefAlt:
        """
        Transform a genotypes matrix via the current haplotype

        Each entry in the returned matrix denotes the presence of each haplotype
        in each chromosome of each sample in the Genotypes object

        Parameters
        ----------
        genotypes : GenotypesRefAlt
            The genotypes which to transform using the current haplotype
        hap_gts: GenotypesRefAlt
            An empty GenotypesRefAlt object into which the haplotype genotypes should
            be stored

        Returns
        -------
        GenotypesRefAlt
            A Genotypes object composed of haplotypes instead of regular variants.
        """
        # Initialize GenotypesRefAlt return value
        if hap_gts is None:
            hap_gts = GenotypesRefAlt(fname=None, log=self.log)
        hap_gts.samples = genotypes.samples
        hap_gts.variants = np.array(
            [(hap.id, hap.chrom, hap.start, 0, "A", "T") for hap in self.data.values()],
            dtype=hap_gts.variants.dtype,
        )
        # Obtain and merge the haplotype genotypes
        self.log.info(
            f"Transforming a set of genotypes from {len(genotypes.variants)} total "
            f"variants with a list of {len(self.data)} haplotypes"
        )
        hap_gts.data = np.concatenate(
            tuple(
                hap.transform(genotypes)[:, np.newaxis] for hap in self.data.values()
            ),
            axis=1,
        ).astype(genotypes.data.dtype)
        return hap_gts
