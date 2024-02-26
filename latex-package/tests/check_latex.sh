#!/bin/env bash
lualatex latex_compat1.tex
lualatex latex_compat2.tex

if cmp --silent -- "latex_compat1.pdf" "latex_compat2.pdf"; then
  echo -e "\e[32mBoth compiled documents are identical!!\e[0m"
else
  echo -e "\e[31mThe documents are different!!\e[0m"
fi
