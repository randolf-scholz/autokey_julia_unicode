# UniCode in PDFLatex

In pdflatex, unicode is implemented using special macros like `\UTFviii@three@octets`

That is a unicode character like `ₖ` is converted into 3 bytes:

1. `\UTFviii@three@octets`
2. Second Byte.
3. Third Byte.

Which is implemented as:

```tex
\long\def\UTFviii@three@octets{%
  \ifincsname
    \expandafter\UTF@three@octets@string
  \else
    \ifx \protect\@typeset@protect \else
      \expandafter\expandafter\expandafter\UTF@three@octets@noexpand
    \fi
  \fi
  \UTFviii@three@octets@combine
}
```

with auxiliary macros:

```tex
\long\def\UTF@three@octets@noexpand#1#2#3#4{\unexpanded{#2#3#4}}
\long\def\UTF@three@octets@string#1#2#3#4{\detokenize{#2#3#4}}
\long\def\UTFviii@three@octets@combine#1#2#3{
    \expandafter\UTFviii@defined\csname u8:\string#1\string#2\string#3\endcsname
}
```

Thus, `\UTFviii@three@octets` expands into

```tex
\expandafter\expandafter\expandafter\UTF@three@octets@noexpand\UTFviii@three@octets@combine
```

the triple `\expandafter`
