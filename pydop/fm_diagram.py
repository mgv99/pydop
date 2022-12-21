
# This file is part of the pydop library.
# Copyright (c) 2021 ONERA.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program. If not, see
# <http://www.gnu.org/licenses/>.
#

# Author: Michael Lienhardt
# Maintainer: Michael Lienhardt
# email: michael.lienhardt@onera.fr

import itertools
import enum


class _empty_c__(object):
  __slots__ = ()
  def __str__(self): return "_empty__"
  def __repr__(self): return "_empty__"

_empty__ = _empty_c__()


################################################################################
# error reporting
################################################################################

##########################################
# 1. feature model naming consistency

class _unbound__c(object):
  __slots__ = ("m_name", "m_path",)
  def __init__(self, name, path=None):
    self.m_name = name
    self.m_path = path
  def __str__(self):
    if(self.m_path is None):
      return f"ERROR: variable \"{self.m_name}\" not declared"
    else:
      return f"ERROR: variable \"{self.m_name}\" not declared in path \"{_path_to_str__(self.m_path)}\""

class _ambiguous__c(object):
  __slots__ = ("m_name", "m_path", "m_paths",)
  def __init__(self, name, path, paths):
    self.m_name  = name
    self.m_path  = path
    self.m_paths = paths
  def __str__(self):
    tmp = ", ".join(f"\"{_path_to_str__(p)}\"" for p in self.m_paths)
    if(self.m_path is None):
      return f"ERROR: reference \"{self.m_name}\" is ambiguous (corresponds to paths: {tmp})"
    else:
      return f"ERROR: reference \"{_path_to_str__(self.m_path)}[{self.m_name}]\" is ambiguous (corresponds to paths: {tmp})"


class _decl_errors__c(object):
  __slots__ = ("m_unbounds", "m_ambiguities",)
  def __init__(self):
    self.m_unbounds = []
    self.m_ambiguities = []

  def add_unbound(self, name, path=None):
    self.m_unbounds.append(_unbound__c(name, path))
  def add_ambiguous(self, name, path, paths):
    self.m_unbounds.append(_ambiguous__c(name, path, paths))

  @property
  def unbounds(self): return self.m_unbounds
  @property
  def ambiguities(self): return self.m_ambiguities

  def has_unbounds(self): return bool(self.m_unbounds)
  def has_ambiguities(self): return bool(self.m_ambiguities)

  def __bool__(self):
    return bool(self.m_unbounds) or bool(self.m_ambiguities)
  def __str__(self):
    return "\n".join(str(el) for l in (self.m_unbounds, self.m_ambiguities) for el in l)


##########################################
# 2. constraint and fm evaluation

class _reason_value_mismatch__c(object):
  __slots__ = ("m_name", "m_ref", "m_val", "m_expected",)
  def __init__(self, ref, val, expected=None):
    self.m_ref = ref
    self.m_val = val
    self.m_expected = expected
  def update_ref(self, updater): self.m_ref = updater(self.m_ref)
  def __str__(self):
    if(expected is None):
      return f"{self.m_ref} vs {self.m_val}"
    else:
      return f"{self.m_ref} vs {self.m_val} (expected: {self.m_expected})"

class _reason_value_none__c(object):
  __slots__ = ("m_ref",)
  def __init__(self, ref):
    self.m_ref = ref
  def update_ref(self, updater): self.m_ref = updater(self.m_ref)
  def __str__(self):
    return f"{self.m_ref} has no value in the input configuration"

class _reason_dependencies__c(object):
  __slots__ = ("m_ref", "m_deps",)
  def __init__(self, ref, deps):
    self.m_ref = ref
    self.m_deps = deps
  def update_ref(self, updater):
    self.m_ref = updater(self.m_ref)
    self.m_deps = tuple(updater(el) for el in self.m_deps)
  def __str__(self):
    tmp = ', '.join(f"\"{el}\"" for el in self.m_deps)
    return f"{self.m_ref} should be True due to dependencies (found: {tmp})"

class _reason_tree__c(object):
  __slots__ = ("m_ref", "m_local", "m_subs", "m_count",)
  def __init__(self, name, idx):
    self.m_ref = f"[{idx}]" if(name is None) else name
    self.m_local = []
    self.m_subs = []
    self.m_count = 0

  def add_reason_value_mismatch(self, ref, val, expected=None):
    self.m_local.append(_reason_value_mismatch__c(ref, val, expected))
    self.m_count += 1
  def add_reason_value_none(self, ref):
    self.m_local.append(_reason_value_none__c(ref))
    self.m_count += 1
  def add_reason_dependencies(self, ref, deps):
    self.m_local.append(_reason_dependencies__c(ref, deps))
    self.m_count += 1  
  def add_reason_sub(self, sub):
    if((isinstance(sub, _eval_result__c)) and (sub.m_reason is not None) and (bool(sub.m_reason))):
      self.m_subs.append(sub.m_reason)
      self.m_count += 1

  def update_ref(self, updater):
    self.m_ref = updater(self.m_ref)
    for el in itertools.chain(self.m_local, self.m_subs):
      el.update_ref(updater)

  def _tostring__(self, indent):
    if(self.m_count == 0):
      return ""
    elif(self.m_count == 1):
      if(self.m_local):
        return f"{indent}{self.m_ref}: {self.m_local[0]}\n"
      else:
        return f"{indent}{self.m_ref}: {self.m_subs[0]}\n"
    else:
      res = f"{indent}{self.m_name}: (\n"
      indent_more = f"{indent} "
      for e in self.m_local:
        res += f"{indent_more}{e}\n"
      for s in self.m_subs:
        res += s._tostring__(indent_more)
      res += f"{indent})\n"
      return res

  def __bool__(self): return (self.m_count != 0)
  def __str__(self): return self._tostring__("")


################################################################################
# constraint and feature model evaluation result
################################################################################

class _eval_result__c(object):
  __slots__ = ("m_value", "m_reason", "m_snodes")
  def __init__(self, value, reason):
    self.m_value  = value   # the result of the evaluation
    self.m_reason = reason  # reason for which the result is not what was expected

  def value(self): return self.m_value
  def __bool__(self): return self.value()

class _eval_result_fd__c(_eval_result__c):
  __slots__ = ("m_nvalue", "m_snodes")
  def __init__(self, value, reason, nvalue, snodes):
    _eval_result__c.__init__(self, value, reason)
    self.m_nvalue = nvalue  # the value of the current feature, used for propagation within a FD
    self.m_snodes = snodes  # the list of sub nodes that are True


################################################################################
# paths and partial paths manipulation
################################################################################

def _path_includes__(p, p_included):
  # print(f"_path_includes__({p}, {p_included})")
  idx_p = 0
  idx_included = 0
  len_p = len(p)
  len_included = len(p_included)
  while(idx_included < len_included):
    if(idx_p < len_p):
      if(p[idx_p] == p_included[idx_included]):
        idx_included += 1
      idx_p += 1
    else:
      # print("  => False")
      return False
  # print("  => True")
  return True

def _path_to_str__(path): return ("None" if(path is None) else "/".join(path))
def _path_from_str__(s): return s.split('/')


def _path_check_exists__(path_s, mapping, errors, additional_path=()):
  path = _path_from_str__(path_s)
  name = path[-1]
  path = (additional_path + tuple(path[0:-1]))
  decls = mapping.get(name)
  if(decls is None):
    errors.add_unbound(name)
  else:
    refs = []
    length = 0
    for el in decls:
      # if(_path_includes__(el[1], path + (path,))):
      if(_path_includes__(el[1], path)):
          refs.append(el)
          length += 1
    if(length == 0):
      errors.add_unbound(path_s, additional_path)
    elif(length > 1):
      # print(f"AMBIGIUTY: {path_s} => {length} | {refs}")
      errors.add_ambiguous(path_s, None, tuple(el[1] for el in refs))
    else:
      path = refs[0][0]
  return path


################################################################################
# Boolean constraints
################################################################################

##########################################
# 1. main class (for all non leaf behavior)

class _expbool__c(object):
  __slots__ = ("m_content",)
  def __init__(self, content):
    self.m_content = tuple(_expbool__c._manage_parameter__(param) for param in content)

  def get_name(self): return self.__class__.__name__

  def __call__(self, product, idx=None, expected=True):
    # print(f"{self.__class__.__name__}.__call__({product}, {idx}, {expected})")
    results = tuple(_expbool__c._eval_generic__(el, product, i, self._get_expected__(el, i, expected)) for i, el in enumerate(self.m_content))
    values = tuple(el.value() for el in results)
    # print(f"  => values  = {values}")
    res = self._compute__(values)
    if(res == expected):
      reason = None
    else:
      reason = _reason_tree__c(self.get_name(), idx)
      for i, el in enumerate(self.m_content):
        reason.add_reason_value_mismatch(el, results[i], self._get_expected__(el, i, expected))
      for r in results:
        reason.add_reason_sub(r)
    return _eval_result__c(res, reason)
 
  def __str__(self): return f"{self.get_name()}({', '.join(str(el) for el in self.m_content)})"

  @staticmethod
  def _eval_generic__(el, product, i, expected):
    if(isinstance(el, _expbool__c)):
      return el(product, i, expected)
    else:
      return product.get(el, el)

  @staticmethod
  def _manage_parameter__(param):
    if(isinstance(param, _expbool__c)):
      return param
    elif(isinstance(param, str)):
      return Var(param)
    else:
      return Lit(param)

  def _check_declarations__(self, path, mapping, errors):
    self.m_content = tuple(map((lambda sub: sub._check_declarations__(path, mapping, errors)), self.m_content))
    return self

##########################################
# 2. leafs

class Var(_expbool__c):
  # override _expbool__c default tree behavior (Var is a leaf)
  __slots__ = ()
  def __init__(self, var):
    self.m_content = var
  def __call__(self, product, idx=None, expected=True):
    global _empty__
    res = product.get(self.m_content, _empty__)
    if(res is _empty__):
      reason = _reason_tree__c(self.get_name(), idx)
      reason.add_reason_value_none(self.m_content)
    else:
      reason = None
    return _eval_result__c(res, reason)

  def _check_declarations__(self, path, mapping, errors):
    self.m_content = _path_check_exists__(self.m_content, mapping, errors, path)
    return self

class Lit(_expbool__c):
  # override _expbool__c default tree behavior (Lit is a leaf)
  __slots__ = ()
  def __init__(self, var):
    self.m_content = var
  def __call__(self, product, idx=None, expected=True):
    return _eval_result__c(self.m_content, None)

  def _check_declarations__(self, path, mapping, errors):
    return self

##########################################
# 3. constraint over non-booleans

class Lt(_expbool__c):
  __slots__ = ()
  def __init__(self, left, right):
    _expbool__c.__init__(self, (left, right,))
  def _compute__(self, values):
    return (values[0] < values[1])
  def _get_expected__(self, el, idx, expected): return None
      
class Leq(_expbool__c):
  __slots__ = ()
  def __init__(self, left, right):
    _expbool__c.__init__(self, (left, right,))
  def _compute__(self, values):
    return (values[0] <= values[1])
  def _get_expected__(self, el, idx, expected): return None

class Eq(_expbool__c):
  __slots__ = ()
  def __init__(self, left, right):
    _expbool__c.__init__(self, (left, right,))
  def _compute__(self, values):
    return (values[0] == values[1])
  def _get_expected__(self, el, idx, expected): return None

class Geq(_expbool__c):
  __slots__ = ()
  def __init__(self, left, right):
    _expbool__c.__init__(self, (left, right,))
  def _compute__(self, values):
    return (values[0] >= values[1])
  def _get_expected__(self, el, idx, expected): return None

class Gt(_expbool__c):
  __slots__ = ()
  def __init__(self, left, right):
    _expbool__c.__init__(self, (left, right,))
  def _compute__(self, values):
    return (values[0] > values[1])
  def _get_expected__(self, el, idx, expected): return None

##########################################
# 4. boolean operators

class And(_expbool__c):
  __slots__ = ()
  def __init__(self, *args):
    _expbool__c.__init__(self, args)
  def _compute__(self, values):
    return all(values)
  def _get_expected__(self, el, idx, expected):
    if(expected is True): return True
    else: return None

class Or(_expbool__c):
  __slots__ = ()
  def __init__(self, *args):
    _expbool__c.__init__(self, args)
  def _compute__(self, values):
    return any(values)
  def _get_expected__(self, el, idx, expected):
    if(expected is not False): return None
    else: return False

class Not(_expbool__c):
  __slots__ = ()
  def __init__(self, arg):
    _expbool__c.__init__(self, (arg,))
  def _compute__(self, values):
    return not values[0]
  def _get_expected__(self, el, idx, expected):
    if(expected is True): return False
    elif(expected is False): return True
    else: return None

class Xor(_expbool__c):
  __slots__ = ()
  def __init__(self, *args):
    _expbool__c.__init__(self, args)
  def _compute__(self, values):
    res = False
    for element in values:
      if(element):
        if(res): return False
        else: res = True
    return res
  def _get_expected__(self, el, idx, expected):
    return None

class Conflict(_expbool__c):
  __slots__ = ()
  def __init__(self, *args):
    _expbool__c.__init__(self, args)
  def _compute__(self, values):
    res = False
    for element in values:
      if(element):
        if(res): return False
        else: res = True
    return True
  def _get_expected__(self, el, idx, expected):
    return None

class Implies(_expbool__c):
  __slots__ = ()
  def __init__(self, left, right):
    _expbool__c.__init__(self, (left, right,))
  def _compute__(self, values):
    return ((not values[0]) or values[1])
  def _get_expected__(self, el, idx, expected):
    return None

class Iff(_expbool__c):
  __slots__ = ()
  def __init__(self, left, right):
    _expbool__c.__init__(self, (left, right,))
  def _compute__(self, values):
    return (values[0] == values[1])
  def _get_expected__(self, el, idx, expected):
    return None


################################################################################
# Attribute Specification
################################################################################

##########################################
# 1. domains

# domains are either a single interval or a list of intervals
# an interval is a pair of integer/float/None values (None state infinite bound)
# e.g., (None, None) is a domain, as well as [(None, -1), (3, 5), (5, None)]

_NoneType = type(None)

def _is_valid_bound(v):
  return isinstance(v, (int, float, _NoneType))

def _add_domain_spec(l, spec):
    if((len(spec) == 2) and _is_valid_bound(spec[0]) and _is_valid_bound(spec[1])):
      spec = (spec,)

    for arg in spec:
      if(not isinstance(arg, (float, int))):
        if((not isinstance(arg, tuple)) or (len(arg) != 2) or (not (_is_valid_bound(arg[0]) and _is_valid_bound(arg[1])))):
          raise ValueError(f"ERROR: expected domain specification (found {arg})")
        else:
          l.append(arg)
      else:
        l.append((arg, arg+1))

def _check_interval(interval, value):
  if((interval[0] is not None) and (value < interval[0])):
    return False
  if((interval[1] is not None) and (value >= interval[1])):
    return False
  return True

def _check_domain(domain, value):
  if(domain):
    for i in domain:
      if(_check_interval(i, value)): return True
    return False
  else:
    return True

##########################################
# 2. attribute specifications

class _fdattribute_c(object): pass

class Class(_fdattribute_c):
  __slots__ = ("m_class")
  def __init__(self, domain):
    self.m_class = domain
  def __call__(self, value):
    return isinstance(value, self.m_class)

class Bool(Class):
  __slots__ = ()
  def __init__(self): Class.__init__(self, bool)

class String(Class):
  __slots__ = ()
  def __init__(self):  Class.__init__(self, str)

class Enum(Class):
  __slots__ = ()
  def __init__(self, domain):
    if(issubclass(domain, enum.Enum)):
       Class.__init__(self, domain)
    else:
      raise ValueError(f"ERROR: expected an enum class (found {domain})")

class Int(Class):
  __slots__ = ("m_domain",)
  def __init__(self, *args):
    Class.__init__(self, int)
    self.m_domain = []
    _add_domain_spec(self.m_domain, args)

  def __call__(self, value):
    if(Class.__call__(self, value)):
      return _check_domain(self.m_domain, value)
    else:
      return False

  def description(self):
    return f'{self.m_domain[0][0]} <= x < {self.m_domain[0][1]}'

class Float(Class):
  __slots__ = ("m_domain",)
  def __init__(self, *args):
    Class.__init__(self, float)
    self.m_domain = []
    _add_domain_spec(self.m_domain, args)

  def __call__(self, value):
    if(Class.__call__(self, value)):
      return _check_domain(self.m_domain, value)
    else:
      return False

class List(Class):
  __slots__ = ("m_size", "m_kind",)
  def __init__(self, size=None, spec=None):
    Class.__init__(self, (list, tuple))
    self.m_size = []
    if(size is not None):
      _add_domain_spec(self.m_size, size)
    self.m_kind = spec

  def __call__(self, value):
    if(Class.__call__(self, value)):
      # print(f"_check_domain({self.m_size}, {len(value)}) = {_check_domain(self.m_size, len(value))}")
      if(_check_domain(self.m_size, len(value))):
        if(self.m_kind is None):
          return True
        else:
          for el in value:
            if(not self.m_kind(el)):
              return False
          return True
    return False

################################################################################
# Feature Diagrams, Generalized as Groups
################################################################################

_default_product_normalization = None

def set_default_product_normalization(f):
  global _default_product_normalization
  _default_product_normalization = f

##########################################
# 1. core implementation

class _fd__c(object):
  __slots__ = (
    "m_norm",       # the product normalization function
    "m_name",       # the optional name of the feature (anonym nodes are possible)
    "m_content",    # the childrens of the current feature
    "m_ctcs",       # the cross-tree constraints at this feature level
    "m_attributes", # the attribute of the feature
    # the following fields are generated only at the root feature of a FD
    "m_lookup",     # mapping {name: [(feature_obj, path)]}: the keys are all the feature/attributes names in the current tree, and the list are all the elements having that name, with their relative path (in tuple format)
    "m_dom",        # mapping {feature_obj -> path}: lists all the features/attributes in the current, and give their path (in string format)
    # the following field is only used at the root feature of a FD during its evaluation
    "m_errors"      # a _reason_tree__c object listing all the errors encountered during the evaluation of the FD
  )

  ##########################################
  # constructor API

  def __init__(self, *args, **kwargs):
  # def __init__(self, name, content, ctcs, attributes):
    global _default_product_normalization
    name, content, ctcs, attributes = _fd__c._manage_constructor_args__(*args, **kwargs)
    self.m_norm = _default_product_normalization
    self.m_name = name
    self.m_content = content
    self.m_ctcs = ctcs
    self.m_attributes = attributes
    self.clean()

  def set_product_normalization(self, f):
    self.m_norm = f

  @staticmethod
  def _manage_constructor_args__(*args, **kwargs):
    # print(f"_manage_constructor_args__({args}, {kwargs})")
    if(bool(args) and isinstance(args[0], str)):
      name = args[0]
      args = args[1:]
    else:
      name = None
    attributes = tuple((key, spec) for key, spec in kwargs.items())
    content = []
    ctcs = []
    for el in args:
      if(isinstance(el, _fd__c)):
        content.append(el)
      elif(isinstance(el, _expbool__c)):
        ctcs.append(el)
      else:
        raise Exception(f"ERROR: unexpected FD subtree (found type \"{el.__class__.__name__}\")")
    return name, content, ctcs, attributes

  ##########################################
  # base API

  @property
  def name(self):
    return self.m_name
  @property
  def children(self):
    return self.m_content
  @property
  def cross_tree_constraints(self):
    return self.m_ctcs
  @property
  def attributes(self):
    return self.m_attributes
  def has_attributes(self):
    return len(self.attributes) != 0
  def is_leaf(self):
    return len(self.children) == 0

  ##########################################
  # generate_lookup API

  def clean(self):
    self.m_lookup = None
    self.m_dom    = None
    self.m_errors = None

  def check(self):
    return self.generate_lookup()

  def generate_lookup(self):
    if(self.m_lookup is None):
      self.m_errors = _decl_errors__c()
      self.m_lookup = {}
      self.m_dom    = {}
      self._generate_lookup_rec__([], 0, self.m_lookup, self.m_dom, self.m_errors)
    return self.m_errors

  def nf_constraint(self, c):
    if(self.m_lookup is None):
      raise ValueError(f"ERROR: a non-root feature cannot put a constraint in normal form (detected feature \"{self}\")")
    errors = _decl_errors__c()
    c = _expbool__c._manage_parameter__(c)
    res = c._check_declarations__(self.m_dom[self], self.m_lookup, errors)
    return (res, errors)

  def nf_product(self, *args):
    if(self.m_lookup is None):
      raise ValueError(f"ERROR: a non-root feature cannot put a product in normal form (detected feature \"{self}\")")
    errors = _decl_errors__c()
    is_true_d = {}
    for i, p in enumerate(args):
      for k, v in self._normalize_product__(p, errors).items():
        is_true_d[k] = (v, i)
    self._make_product_rec_1(is_true_d)
    # print("=====================================")
    # print("is_true_d")
    # print(is_true_d)
    # print("=====================================")
    res = {}
    v_local = is_true_d.get(self, _empty__)
    if(v_local is _empty__):
      self._make_product_rec_2(False, is_true_d, res)
    else:
      self._make_product_rec_2(v_local[0], is_true_d, res)
    # print(f" => {res}")
    return (res, errors)

  ##########################################
  # call API

  def __call__(self, product, expected=True):
    if(self.m_dom is None):
      raise ValueError("ERROR: evaluating a non well-formed Feature Model (call 'check()' on it before)")
    # reason = _reason_tree__c(self, 0)
    # for el in self.m_dom.keys():
    #   if(el not in product): reason.add_reason_value_none(el)
    # if(bool(reason)): res = _eval_result_fd__c(False, reason, False, ())
    # else: res = self._eval_generic__(product, _fd__c._f_get_deep__, expected)
    res = self._eval_generic__(product, _fd__c._f_get_deep__, expected)
    reason = res.m_reason
    if(reason):
      reason.update_ref(self._updater__)
      pass
    return res

  def _eval_generic__(self, product, f_get, expected=True):
    # print(f"_eval_generic__([{self.__class__.__name__}]{self.m_path}, {product}, {f_get}, {expected})")
    # print(f"_eval_generic__([{self.__class__.__name__}]{_path_to_str__(self.m_path)})")
    # print(f"_eval_generic__({_path_to_str__(self.m_path)})")
    expected_att = (_empty__ if(expected is False) else expected)

    results_content = tuple(f_get(el, product, self._get_expected__(el, i, expected)) for i, el in enumerate(self.m_content))
    # print(f" => computed results_content: {results_content}")
    # print(f"   reasons = {', '.join(str(el.m_reason) for el in results_content)}")
    result_att = tuple(self._manage_attribute__(el, product, i, self._get_expected__(el, i, expected)) for i, el in enumerate(self.m_attributes))
    # print(f" => computed result_att: {result_att}")
    # print(f"   reasons = {', '.join(str(el.m_reason) for el in result_att)}")
    result_ctc = tuple(_expbool__c._eval_generic__(el, product, i, self._get_expected__(el, i, expected)) for i, el in enumerate(self.m_ctcs))
    # print(f" => computed result_ctc: {result_ctc}")
    # print(f"   reasons = {', '.join(str(el.m_reason) for el in result_ctc)}")


    nvalue_subs  = tuple(itertools.chain((el.m_nvalue for el in results_content), (el.m_value for resu in (result_att, result_ctc) for el in resu)))
    # nvalue_local = product.get(self, _empty__)
    nvalue_local = None
    # print(f"  => compute {nvalue_subs}, {nvalue_local}")
    nvalue_sub = self._compute__(nvalue_subs, nvalue_local)
    # print(f"  => nvalue_sub = {nvalue_sub}")
    value_subs = all(el.m_value for el in results_content)
    snodes = tuple(v for el in results_content for v in el.m_snodes)

    # print(f" => computed res: {res}")

    # check consistency with name
    reason = None
    if(self.m_name is not None):
      nvalue_local = product.get(self, _empty__)
      if(nvalue_local is _empty__): # should never occur
        reason = _reason_tree__c(self, 0)
        reason.add_reason_value_none(self)
        # reason = f"Feature {_path_to_str__(self.m_path)} has no value in the input product"
      elif((not nvalue_local) and snodes):
        reason = _reason_tree__c(self, 0)
        reason.add_reason_dependencies(self, snodes)
        # tmp = ', '.join(f"\"{_path_to_str__(el.m_path)}\"" for el in snodes)
        # reason = f"Feature {_path_to_str__(self.m_path)} should be set to True due to validated subfeatures (found: {tmp})"
      elif(nvalue_local and (not nvalue_sub)):
        reason = _reason_tree__c(self, 0)
        reason.add_reason_value_mismatch(self, True, False)
        # reason = f"Feature {_path_to_str__(self.m_path)} is selected while its content is False"
      elif(nvalue_local):
        snodes = snodes + (self,)
    else:
      nvalue_local = nvalue_sub

    value = value_subs and (reason is None)
    # print(f"  => nvalue_local = {nvalue_local}")
    # print(f"  => value = {value}")

    if((nvalue_local != expected) or (not value)):
      if(reason is None): reason = _reason_tree__c(self, 0)
      if((nvalue_local != expected)):
        reason.add_reason_value_mismatch(self, nvalue_local, expected)
      for el in itertools.chain(results_content, result_att, result_ctc):
        reason.add_reason_sub(el)

    return _eval_result_fd__c(value, reason, nvalue_local, snodes)

  def _f_get_shallow__(self, product, expected=True):
    if(self.m_name is None):
      return self._eval_generic__(product, _fd__c._f_get_shallow__, expected)
    else:
      nvalue = product.get(self, _empty__)
      if(v is _empty__):
        reason = _reason_tree__c(self, 0)
        reason.add_reason_value_none(self)
        value = False
        nvalue = False
        return _eval_result_fd__c(value, reason, nvalue, ())
      else:
        return _eval_result_fd__c(True, None, nvalue, ())

  def _f_get_deep__(self, product, expected=True):
    return self._eval_generic__(product, _fd__c._f_get_deep__, expected)

  def _manage_attribute__(self, att, product, idx, expected):
    name, spec = att
    value = product.get(att, _empty__)
    if(value is _empty__):
      if(expected):
        reason = _reason_tree__c(self, 0)
        reason.add_reason_value_none(att)
        return _eval_result__c(False, reason)
        # return _eval_result__c(False, _reason_tree__c(name, idx, "Attribute has no value in the input product"))
      else:
        return _eval_result__c(False, None)
    else:
      res = spec(value)
      if(expected == res):
        return _eval_result__c(res, None)
      else:
        reason = _reason_tree__c(self, 0)
        reason.add_reason_value_mismatch(att, res, expected)
        return _eval_result__c(res, reason)
        # return _eval_result__c(res, _reason_tree__c(name, idx, f"Attribute has erroneous value \"{value}\" => specification returns {res}"))

  ##########################################
  # internal: lookup generation

  def _generate_lookup_rec__(self, path_to_self, idx, lookup, dom, errors):
    # print(f"_generate_lookup_rec__({self.m_name}, {idx}, {path_to_self}, {lookup}, {errors})")
    # 1. if local names, add it to the table, and check no duplicates
    path_to_self.append(str(idx) if(self.m_name is None) else self.m_name)
    local_path = tuple(path_to_self)
    if(self.m_name is not None):
      _fd__c._check_duplicate__(self, self.m_name, local_path, lookup, errors)
      dom[self] = _path_to_str__(local_path)
    # 2. add subs
    for i, sub in enumerate(self.m_content):
      sub._generate_lookup_rec__(path_to_self, i, lookup, dom, errors)
    # 3. add attributes
    for att_def in self.m_attributes:
      _fd__c._check_duplicate__(att_def, att_def[0], local_path, lookup, errors)
      dom[att_def] = _path_to_str__(local_path + (att_def[0],))
    # 4. check ctcs
    self.m_ctcs = tuple(ctc._check_declarations__(local_path, lookup, errors) for ctc in self.m_ctcs)
    # 5. reset path_to_self
    path_to_self.pop()

  @staticmethod
  def _check_duplicate__(el, name, path, res, errors):
    # print(f"_check_duplicate__({el}, {name}, {path}, {res})")
    tmp = res.get(name)
    if(tmp is not None):
      others = []
      for obj, path_other in tmp:
        if(_path_includes__(path, path_other)):
          others.append(path_other)
      if(bool(others)):
        errors.add_ambiguous(name, path, others)
      tmp.append( (el, path,) )
    else:
      res[name] = [(el, path,)]

  ##########################################
  # internal: product nf API

  def _normalize_product__(self, product, errors):
    res = {}
    if(self.m_norm is not None):
      product = self.m_norm(self, product)
    for key, val in product.items():
      if(isinstance(key, str)):
        res[_path_check_exists__(key, self.m_lookup, errors)] = val
      else:
        res[key] = val
    return res

  def _make_product_rec_1(self, is_true_d):
    idx, v_local, v_subs = self._infer_sv__(is_true_d)
    self._make_product_update__(is_true_d, idx, v_local, v_subs)
    for sub in self.m_content:
      sub._make_product_rec_1(is_true_d)
    idx, v_local, v_subs = self._infer_sv__(is_true_d)
    self._make_product_update__(is_true_d, idx, v_local, v_subs)

  def _make_product_update__(self, is_true_d, idx, v_local, v_subs):
    if(v_local is not _empty__):
      is_true_d[self] = (v_local, idx)
    for sub, v_sub in zip(self.m_content, v_subs):
      if(v_sub is not _empty__):
        is_true_d[sub] = (v_sub, idx)

  def _make_product_rec_2(self, v_local, is_true_d, res):
    # _, _, v_subs = self._make_product_extract__(is_true_d)
    # print(f"  {self} :subs[0] => {v_subs}")
    _, _, v_subs = self._infer_sv__(is_true_d)
    # print(f"  {self} :subs[1] => {v_subs}")
    res[self] = v_local
    for sub, v_sub in zip(self.m_content, v_subs):
      if(v_sub is _empty__):
        sub._make_product_rec_2(False, is_true_d, res)
      else:
        sub._make_product_rec_2(v_sub, is_true_d, res)
    # if feature selected, need to include the attribute 
    if(v_local):
      for att_def in self.m_attributes:
        v = is_true_d.get(att_def, _empty__)
        if(v is not _empty__):
          res[att_def] = v[0]

  @staticmethod
  def _make_product_extract_utils__(is_true_d, domain, expected=True):
    idx = -1
    if(expected is None):
      value = _empty__
      def f(val):
        nonlocal idx
        nonlocal value
        if(val is _empty__): 
          return val
        else:
          if(val[1] > idx):
            idx = val[1]
            value = val[0]
          return val[0]
      for sub in domain:
        f(is_true_d.get(sub, _empty__))
      return idx, value
    else:      
      def f(val):
        nonlocal idx
        if(val is _empty__): 
          return val
        else:
          if((val[0] == expected) and (val[1] > idx)):
            idx = val[1]
          return val[0]
      v_subs = tuple(f(is_true_d.get(sub, _empty__)) for sub in domain)
      return idx, v_subs



  ##########################################
  # print for error report

  def _updater__(self, ref):
    return self.m_dom.get(ref, ref)

  def __str__(self):
    return "TMP"
    # if(self.m_path is None):
    #   return object.__str__(self)
    # else:
    #   return _path_to_str__(self.m_path)

  def __repr__(self): return str(self)
  




class FDAnd(_fd__c):
  def __init__(self, *args, **kwargs):
    _fd__c.__init__(self, *args, **kwargs)
  def _compute__(self, values, nvalue):
    return all(values)
  def _get_expected__(self, el, i, expected):
    return (True if(expected) else None)
  def _infer_sv__(self, is_true_d):
    idx, value = self._make_product_extract_utils__(is_true_d, itertools.chain((self,), self.m_content), expected=None)
    def get_default(el):
      val = is_true_d.get(el, _empty__)
      if((val is _empty__) or (val[1] < idx)):
        return value
      else:
        return val[0]
    v_local = get_default(self)
    return idx, v_local, tuple(get_default(sub) for sub in self.m_content)


class FDAny(_fd__c):
  def __init__(self, *args, **kwargs):
    _fd__c.__init__(self, *args, **kwargs)
  def _compute__(self, values, nvalue):
    return True
  def _get_expected__(self, el, i, expected):
    return None
  def _infer_sv__(self, is_true_d):
    # tuple((is_true_d.get(sub, (_empty__, -1))[0]) for sub in self.m_content)
    idx_subs, v_subs = self._make_product_extract_utils__(is_true_d, self.m_content)
    v_local, idx_local = is_true_d.get(self, (False, -1))
    if(idx_subs > idx_local):
      idx_local = idx_subs
      v_local = True
    return idx_local, v_local, v_subs


class FDOr(_fd__c):
  def __init__(self, *args, **kwargs):
    _fd__c.__init__(self, *args, **kwargs)
  def _compute__(self, values, nvalue):
    return any(values)
  def _get_expected__(self, el, i, expected):
    return (False if(not expected) else None)
  def _infer_sv__(self, is_true_d):
    # tuple((is_true_d.get(sub, (_empty__, -1))[0]) for sub in self.m_content)
    idx_subs, v_subs = self._make_product_extract_utils__(is_true_d, self.m_content)
    v_local, idx_local = is_true_d.get(self, (False, -1))
    if(idx_subs > idx_local):
      idx_local = idx_subs
      v_local = True
    return idx_local, v_local, v_subs

class FDXor(_fd__c):
  def __init__(self, *args, **kwargs):
    _fd__c.__init__(self, *args, **kwargs)
  def _compute__(self, values, nvalue):
    res = False
    for element in values:
      if(element):
        if(res): return False
        else: res = True
    return res
  def _get_expected__(self, el, i, expected):
    return None
  def _infer_sv__(self, is_true_d):
    idx_subs, v_subs = self._make_product_extract_utils__(is_true_d, self.m_content)
    v_local, idx_local = is_true_d.get(self, (False, -1))
    if(idx_subs > idx_local):
      idx_local = idx_subs
      v_local = True
    if(idx_subs > -1):
      v_subs = tuple((is_true_d.get(sub, (False, -1)) == (True, idx_subs)) for sub in self.m_content)
    return idx_local, v_local, v_subs


class FD(FDAnd): pass

