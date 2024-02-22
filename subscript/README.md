# This is a Readme!

```tex
\def\newunicodechar#1#2{%
    \@tempswafalse
    \edef\nuc@tempa{\detokenize{#1}}%
    \if\relax\nuc@tempa\relax
        \nuc@emptyargerr
    \else
        \edef\@tempb{\expandafter\@car\nuc@tempa\@nil}%
        \nuc@check
        \if@tempswa
            \@ifundefined{u8:\nuc@tempa}{}{%
                \PackageWarning{newunicodechar}{%
                    Redefining Unicode character\ifdefined\nuc@verbose; it meant\MessageBreak ***\space\space\nuc@meaning\space\space***\MessageBreakbefore your redefinition\fi
                }
            }%
        \@namedef{u8:\nuc@tempa}{#2}%
    \fi
\fi
}
```

```tex
\gdef\DeclareUnicodeCharacter#1#2{%
  \count@"#1\relax
  \wlog{ \space\space defining Unicode char U+#1 (decimal \the\count@)}%
  \begingroup
    \parse@XML@charref
    \def\UTFviii@two@octets##1##2{\csname u8:##1\string##2\endcsname}%
    \def\UTFviii@three@octets##1##2##3{\csname u8:##1%
                                     \string##2\string##3\endcsname}%
    \def\UTFviii@four@octets##1##2##3##4{\csname u8:##1%
                           \string##2\string##3\string##4\endcsname}%
    \expandafter\expandafter\expandafter
    \expandafter\expandafter\expandafter
    \expandafter
     \gdef\UTFviii@tmp{\IeC{#2}}%
   \endgroup
}
```
