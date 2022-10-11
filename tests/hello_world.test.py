
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


from pydop.spl import SPL, RegistryGraph
from pydop.fm_core import make_configuration
from pydop.fm_diagram import *
from pydop.operations.modules import VariantModules

import enum
import sys

class Hello(enum.Enum):
  english="Hello"
  german="Guten Tag"
  spanish="hola"
  french="Bonjour"


if(__name__ == "__main__"):

  hello_world_fm = FD("HelloWorld",
    FDAnd(
      FD("lang", lang_v=Enum(Hello)),
    ),
    FDAny(
      FD("times", times_v=Int(0,None))
    )
  )

  spl = SPL(hello_world_fm, RegistryGraph(), VariantModules("hw"))

  @spl.delta(True)
  def setup_hw(variant):
    @variant.hw.add
    class HW(object): pass

  def gen_print_core(hw_str):
    def print_core(self, name):
      print(f"{hw_str} {name}")
    return print_core

  def gen_print(nb):
    def print(self, name):
      for i in range(nb):
        self.print_core(name)
    return print


  @spl.delta("lang")
  def setup_core(variant, product):
    hw_str = product["lang_v"].value
    variant.hw.HW.add(gen_print_core(hw_str))

  @spl.delta("times")
  def setup_print_1(variant, product):
    nb = product["times_v"]
    variant.hw.HW.add(gen_print(nb))

  @spl.delta(Not("times"))
  def setup_print_2(variant):
    @variant.hw.HW.add
    def print(self, name):
      self.print_core(name)


  # English
  conf_1 = { "HelloWorld": True, "lang": True, "lang_v": Hello.english, "times": True, "times_v": 2 };
  variant = spl(conf_1)
  variant.register_modules()
  from hw import HW
  HW().print("John")

  #cleanup
  variant.unregister_modules()

  # German
  # conf_2 = { "HelloWorld": True, "hello": True, "lang_v": Hello.german, "times": True, "times_v": 3 };
  conf_2 = hello_world_fm.combine_product(conf_1, { "lang_v": Hello.german, "times_v": 3 })
  assert(conf_2 == { "HelloWorld": True, "lang": True, "lang_v": Hello.german, "times": True, "times_v": 3 })
  variant = spl(conf_2)
  variant.register_modules()
  from hw import HW
  HW().print("Mia")
  variant.unregister_modules()

  # no repeat
  # conf_3 = { "HelloWorld": True, "hello": True, "lang_v": Hello.spanish, "times": False };
  conf_3 = hello_world_fm.combine_product(conf_2, { "lang_v": Hello.spanish, "times": False })
  assert(conf_3 == { "HelloWorld": True, "lang": True, "lang_v": Hello.spanish, "times": False })
  variant = spl(conf_3)
  variant.register_modules()
  from hw import HW
  HW().print("Luciana")

  variant.unregister_modules()



  ##########################################
  #check failure

  # 1. missing decl
  conf_err1 = {}
  try:
    variant = spl(conf_err1)
    print("ERROR in missing feature")
  except KeyError: pass

  # 2. wrong group
  conf_err2 = { "HelloWorld": True, "lang": False, "times": True, "times_v": 4 };
  try:
    variant = spl(conf_err2)
    print("ERROR in wrong group")
  except ValueError: pass

  # 3. bad attribute 1/2
  conf_err3 = { "HelloWorld": True, "lang": True, "lang_v": 1, "times": True, "times_v": 4 };
  try:
    variant = spl(conf_err3)
    print("ERROR in bad attribute 1/2")
  except ValueError: pass

  # 4. bad attribute 2/2
  conf_err4 = { "HelloWorld": True, "lang": True, "lang_v": Hello.french, "times": False, "times_v": 4 };
  try:
    variant = spl(conf_err4)
    print("ERROR in bad attribute 2/2")
  except ValueError: pass


  conf1 = {"lang": True, "lang_v": 1, "times": True, "times_v": 4}
  conf2 = make_configuration(conf1)
  assert(conf2 == conf1)
  conf3 = hello_world_fm.make_product(conf2)
  assert(conf3 == conf_err3)






