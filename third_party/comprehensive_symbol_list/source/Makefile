#############################################
# Build the Comprehensive LaTeX Symbol List #
# By Scott Pakin <scott+clsl@pakin.org>     #
#############################################

# Define TARGETS as a list of all of the files we intend to generate.
TARGETS = symbols-letter.pdf symbols-a4.pdf \
	  rawtables-letter.pdf rawtables-a4.pdf \
	  SYMLIST README

# There are a few files that we didn't generate but that need to be
# included in a source distribution.
PRUNETOML = \
	prune-idx-delete.toml \
	prune-idx-accents.toml \
	prune-idx-arrows.toml \
	prune-idx-brands.toml \
	prune-idx-circles.toml \
	prune-idx-cup-cap.toml \
	prune-idx-equals.toml \
	prune-idx-flags.toml \
	prune-idx-hands.toml \
	prune-idx-harpoons.toml \
	prune-idx-ineqs.toml \
	prune-idx-integrals.toml \
	prune-idx-letters.toml \
	prune-idx-math-maps.toml \
	prune-idx-music.toml \
	prune-idx-prec-succ.toml \
	prune-idx-rhombuses.toml \
	prune-idx-sets.toml \
	prune-idx-similar.toml \
	prune-idx-squares.toml \
	prune-idx-stars.toml \
	prune-idx-triangles.toml \
	prune-idx-turnstiles.toml \
	prune-idx-wedges-vees.toml \
	prune-idx-rewrite.toml \
	prune-idx-merge.toml \
	prune-idx-see.toml
EXTRADIST = symbols.tex lightbulb10.mf lightbulb.mf \
	    symbols.ist fakego.sty unicode2eps.pe fakeold-arrows.sty \
	    makefakeMnSymbol teubner-subset.sty fakemusixtex.sty \
	    fakearevmath.sty fakedozenal.sty fakelatexsym.sty \
	    makefakefdsymbol makefakeboisik fakearcs.sty fakeallrunes.sty \
	    renamed-overarrows.sty makefakestix makefakestarfont \
	    makerawtables makefakecmupint makefakeworldflags \
	    makefakelualatex makefakeasapsym makefakefigchild \
	    patch-idx prune-idx $(PRUNETOML) \
	    makefakeutfsym maketitlepage makeREADME unicode.txt Makefile

# All formats of the symbol list depend upon the following files.
COMMONDEPS = symbols.tex symbols.ist fakeMnSymbol.sty teubner-subset.sty \
	     fakemusixtex.sty fakeknitting.sty fakefdsymbol.sty \
	     fakeboisik.sty fakestix.sty fakearcs.sty fakeold-arrows.sty \
	     fakearevmath.sty fakedozenal.sty fakelatexsym.sty \
	     fakestarfont.sty nonlatex versatim.tex junicode lilyglyphs \
	     fakeallrunes.sty fakecmupint.sty fakeworldflags.sty \
	     fakeacademicons.sty faketypicons.sty renamed-overarrows.sty \
	     fakeasapsym.sty fakefontmfizz.sty fakehamnosys.sty \
	     fakefigchild.sty fakeutfsym.sty fakelogix.sty \
	     lightbulb.pdf lightbulb.eps lightbulb10.pfb lightbulb.map \
	     patch-idx prune-idx $(PRUNETOML)

# The following non-LaTeX files will be copied to the current
# directory if they exist so LaTeX can find them.
NONLATEX = hands.mf greenpoint.mf nkarta.mf astrosym.mf WebOMintsGD.pfb \
	   moonphase.mf dancers.mf smfpr10.mf umranda.mf umrandb.mf \
	   cryst.mf dice3d.mf magic.mf fselch10.mf Junicode.ttf msym10.tfm \
	   knot1.mf knot2.mf knot3.mf knot4.mf knot5.mf knot6.mf knot7.mf \
	   endofproofwd.pdf cmrj.tfm

# We need FontForge (or the older PfaEdit) to generate lightbulb10.pfb.
FONTFORGE = fontforge

# Specify how much process parallelism we should employ in xargs invocations.
PARXARGS = $(shell lscpu --parse=CPU | grep -Evc '^#')

# The following should be overwritten in a recursive call to Make.
SIZE = letter

# The document builds properly only with pdflatex.
LATEX = pdflatex

# I've had some trouble using sh as the shell.  bash seems to work, though.
SHELL = /bin/bash

###########################################################################

# Build all specified formats in all specified paper sizes.
all: check_version $(TARGETS)

###########################################################################

# Define a generic rule for building the document for either U.S. Letter
# or A4 paper.
symbols symbols-$(SIZE)-full.ind &: $(COMMONDEPS)
	# Remove old index files to speed up the first two passes.
	# (Technically, only the .ind file needs to be removed.)
	$(RM) symbols-$(SIZE).ind symbols-$(SIZE).idx symbols-$(SIZE).ilg symbols-$(SIZE)-full.ind symbols-$(SIZE)-full.idx
	# Pass 1: Produce an initial build of the document.
	$(LATEX) -jobname symbols-$(SIZE) '\PassOptionsToClass{$(SIZE)paper}{article}\input symbols'
	# Pass 2: Perform multiple partial and one full build to generate
	# a title page.
	./patch-idx symbols-$(SIZE).idx
	./maketitlepage symbols-$(SIZE).idx $(SIZE)
	# Pass 3: Build again to produce a final page layout.
	$(LATEX) -jobname symbols-$(SIZE) '\PassOptionsToClass{$(SIZE)paper}{article}\input symbols'
	# Create an index based on the current layout.  We do some
	# postprocessing of the .idx file to improve usability.  However,
	# we back up the pre-pruned list so we later can get an accurate
	# symbol count.
	./patch-idx symbols-$(SIZE).idx
	makeindex -s symbols.ist symbols-$(SIZE)
	cp symbols-$(SIZE).ind symbols-$(SIZE)-full.ind
	./prune-idx symbols-$(SIZE).idx $(PRUNETOML)
	makeindex -s symbols.ist symbols-$(SIZE)
	# Pass 4: Build the document with the newly generated index.
	# Afterward, the table of contents and PDF bookmarks files should
	# point to the correct index pages, but these are not yet
	# incorporated into the document.
	$(LATEX) -jobname symbols-$(SIZE) '\PassOptionsToClass{$(SIZE)paper}{article}\input symbols'
	# Get a final symbol count, and put it in the .aux file.
	totalsymbols=`grep -E -c '\\\\item \\\\(sp)?verb' symbols-$(SIZE)-full.ind` ; \
	  ( fgrep -v prevtotalsymbols symbols-$(SIZE).aux > symbols-$(SIZE).pts ; \
	    echo "\\gdef\\prevtotalsymbols{$$totalsymbols}" ; \
	    echo "\\gdef\\approxcount{}" ) >> symbols-$(SIZE).pts ; \
	  mv symbols-$(SIZE).pts symbols-$(SIZE).aux
	# Pass 5: Build the final document using the final symbol count
	# and with the table of contents and PDF bookmarks correctly
	# reflecting the index pages.
	$(LATEX) -jobname symbols-$(SIZE) '\PassOptionsToClass{$(SIZE)paper}{article}\def\titlefile{title-$(SIZE)}\input symbols'
	-@(grep --color -E "^.*multiply.defined.*" symbols-$(SIZE).log ; true)
	-@(grep --color -E "^.*undefined.*" symbols-$(SIZE).log | grep -v U/stmry/b/n ; true)

# Define a single-pass version of the above to reduce build time during
# development work.
fast-symbols: $(COMMONDEPS)
	$(LATEX) -jobname symbols-$(SIZE) '\PassOptionsToClass{$(SIZE)paper}{article}\input symbols'

check_version: symbols.tex
	comment_ver=$$(perl -ne '/^\%\%\%\s+version\s+=\s+\"(\S+)\"/ && print "$$1\n"' symbols.tex) \
	pdf_ver=$$(perl -ne '/pdfversionid\s*=\s*\{(\S+)\}/ && print "$$1\n"' symbols.tex) ; \
	test "$$comment_ver" = "$$pdf_ver"

###########################################################################

# Define specific rules for building with different pages sizes.
symbols-a4.pdf symbols-a4.log &: $(COMMONDEPS)
	if [ -z "$(FAST)" ] ; then \
	    $(MAKE) $(MAKEFLAGS) SIZE=a4 symbols ; \
	else \
	    $(MAKE) $(MAKEFLAGS) SIZE=a4 fast-symbols ; \
	fi

symbols-letter.pdf symbols-letter.log &: $(COMMONDEPS)
	if [ -z "$(FAST)" ] ; then \
	    $(MAKE) $(MAKEFLAGS) SIZE=letter symbols ; \
	else \
	    $(MAKE) $(MAKEFLAGS) SIZE=letter fast-symbols ; \
	fi

rawtables-letter.tex rawtables-letter.list testfont-letter.pdf testfont-letter.log &: makerawtables $(COMMONDEPS)
	./makerawtables --paper=letter

rawtables-letter.pdf: rawtables-letter.tex
	pdftex rawtables-letter.tex

rawtables-a4.tex rawtables-a4.list testfont-a4.pdf testfont-a4.log &: makerawtables $(COMMONDEPS)
	./makerawtables --paper=a4

rawtables-a4.pdf: rawtables-a4.tex
	pdftex rawtables-a4.tex

###########################################################################

lightbulb.pdf: lightbulb.eps
	ps2pdf -dEPSCrop lightbulb.eps

lightbulb.eps: lightbulb10.mf lightbulb.mf
	mpost -mem=mfplain '\mode:=proof; prologues:=2; labelfont cmr17; input lightbulb10'
	mv lightbulb10.65 lightbulb.eps

# Generate a FontForge script that makes the LightBulb10 PostScript
# names mixed case.
lightbulb10.pe:
	echo 'Open($$1);' > $@
	echo 'LB = "LightBulb";' >> $@
	echo 'SetFontNames(LB+"10", LB, LB+"10");' >> $@
	echo 'Generate("lightbulb10.pfb");' >> $@

# Define a rule to produce a Type 1 version of the LightBulb10 font.
lightbulb10.pfb: lightbulb10.mf lightbulb10.pe
	mftrace -V -fpfb --simplify lightbulb10
	$(FONTFORGE) -script lightbulb10.pe lightbulb10.pfb

# Define a rule to produce a LightBulb font-mapping file.
lightbulb.map:
	echo "lightbulb10 LightBulb10 <lightbulb10.pfb" > lightbulb.map

###########################################################################

# If we have MnSymbol.sty, generate a faked version that does not
# declare any new math alphabets.
fakeMnSymbol.sty: makefakeMnSymbol
	if [ "`kpsewhich MnSymbol.sty`" ] ; then \
	  ./makefakeMnSymbol `kpsewhich MnSymbol.sty` > $@ ; \
	else \
	  ./makefakeMnSymbol /dev/null > $@ ; \
	fi

# If we have fdsymbol.sty, generate a faked version that does not
# declare any new math alphabets.
fakefdsymbol.sty: makefakefdsymbol
	if [ "`kpsewhich fdsymbol.sty`" ] ; then \
	  ./makefakefdsymbol `kpsewhich fdsymbol.sty` > $@ ; \
	else \
	  ./makefakefdsymbol /dev/null > $@ ; \
	fi

# If we have boisik.sty, generate a faked version that does not
# declare any new math alphabets.
fakeboisik.sty: makefakeboisik
	if [ "`kpsewhich boisik.sty`" ] ; then \
	  ./makefakeboisik `kpsewhich boisik.sty` > $@ ; \
	else \
	  ./makefakeboisik /dev/null > $@ ; \
	fi

# If we have Junicode.ttf, extract the versicle and response
# characters as graphical images.  This enables the font to work in
# any TeX engine and without any helper .tfm or .enc files.
junicode: unicode2eps.pe
	for jfont in Junicode-Regular.otf Junicode-Regular.ttf Junicode.otf Junicode.ttf JunicodeTwoBeta-Regular.otf ; do \
	  if [ "`kpsewhich $$jfont`" ] ; then \
	    jfont_full=$$(readlink -f $$(kpsewhich $$jfont)) ; \
	    test -e junicode || mkdir junicode ; \
	    cd junicode ; \
	    $(FONTFORGE) -script ../unicode2eps.pe `kpsewhich $$jfont_full` 0x2123 0x211F ; \
	    ls *.eps | xargs -P$(PARXARGS) -t -i epstopdf '{}' ; \
	    true ; \
            break ; \
	  fi ; \
        done

# If we have knitting.sty, generate a truncated version that excludes
# some catcode trickery which breaks mylatex.ltx.
fakeknitting.sty:
	echo "% This is a truncated version of knitting.sty for use only" > $@
	echo "% with the Comprehensive LaTeX Symbol List." >> $@
	echo "" >> $@
	if [ "`kpsewhich knitting.sty`" ] ; then \
	  cat `kpsewhich knitting.sty` | sed '/Standard chart commands/,$$d' >> $@ ; \
	fi

# If we have stix.sty, generate a faked version that does not
# declare any new math alphabets.
fakestix.sty: makefakestix
	if [ "`kpsewhich stix.sty`" ] ; then \
	  ./makefakestix `kpsewhich stix.sty` > $@ ; \
	else \
	  ./makefakestix /dev/null > $@ ; \
	fi

# If we have starfont.sty, generate a faked version that does not
# declare any new math alphabets.
fakestarfont.sty: makefakestarfont
	if [ "`kpsewhich starfont.sty`" ] ; then \
	  ./makefakestarfont `kpsewhich starfont.sty` > $@ ; \
	else \
	  ./makefakestarfont /dev/null > $@ ; \
	fi

# If we have cmupint.sty, generate a faked version that does not
# declare any new math alphabets.
fakecmupint.sty: makefakecmupint
	if [ "`kpsewhich cmupint.sty`" ] ; then \
	  ./makefakecmupint `kpsewhich cmupint.sty` > $@ ; \
	else \
	  ./makefakecmupint /dev/null > $@ ; \
	fi

# The apl package's versatim.tex messes up TeX's category codes.
# Hence, we override that file with a do-nothing version.
versatim.tex:
	echo "% Do-nothing replacement for the apl package's versatim.tex" > $@
	echo "\\endinput" >> $@

# If we have the Emmentaler music fonts, convert each glyph to a
# graphical image, which we place in our lilyglyphs subdirectory.
# With a few command redefinitions, this enables us to use lilyglyphs
# without requiring XeLaTeX or LuaLaTeX.
lilyglyphs: extract-by-name.pe
	test -e lilyglyphs || mkdir lilyglyphs
	if [ "`kpsewhich emmentaler-16.otf`" ] ; then \
	  cd lilyglyphs ; \
	  $(FONTFORGE) -script ../extract-by-name.pe `kpsewhich emmentaler-16.otf` ; \
	  mv accidentals.sharp.slashslashslash.stemst.eps accidentals.sharp.slashslashslash.stemstem.eps ; \
	  mv accidentals.sharp.slashslash.stemstemste.eps accidentals.sharp.slashslash.stemstemstem.eps ; \
	  ls *.eps | xargs -P$(PARXARGS) -t -i epstopdf '{}' ; \
	  rm -f lilyglyphs_logo.pdf ; \
	  ln -s -f `texdoc -l -I lilyglyphs_logo.pdf | awk 'NR==1 {print $$2}'` . ; \
	fi

# If we have worldflags.sty, generate a faked version that does not
# declare any short-named global symbols and that renders much faster.
fakeworldflags.sty: makefakeworldflags
	if [ "`kpsewhich worldflags.sty`" ] ; then \
	  ./makefakeworldflags ; \
	else \
	  touch fakeworldflags.sty ; \
	fi

# If we have academicons.sty, generate a faked version that works
# with pdfLaTeX.
FAKEACADEMICONS_GEN = \
	fakeacademicons.sty \
	fakeacademicons.enc \
	fakeacademicons.tfm
$(FAKEACADEMICONS_GEN) &: makefakelualatex
	if [ "`kpsewhich academicons.sty`" ] ; then \
	  ./makefakelualatex academicons academicons.ttf ; \
	else \
	  touch fakeacademicons.sty ; \
	fi

# If we have typicons.sty, generate a faked version that works
# with pdfLaTeX.
FAKETYPICONS_GEN = \
	faketypicons.sty \
	faketypiconsA.enc \
	faketypiconsA.tfm \
	faketypiconsB.enc \
	faketypiconsB.tfm
$(FAKETYPICONS_GEN) &: makefakelualatex
	if [ "`kpsewhich typicons.sty`" ] ; then \
	  ./makefakelualatex typicons typicons.ttf ; \
	else \
	  touch faketypicons.sty ; \
	fi

# If we have asapsym.sty, generate a faked version that works with
# pdfLaTeX.
FAKEASAPSYM_GEN = \
	Asap-Symbol.pfb \
	fakeasapsym.sty \
	fakeasapsym.enc \
	fakeasapsym.tfm
$(FAKEASAPSYM_GEN) &: makefakeasapsym
	if [ "`kpsewhich asapsym.sty`" ] ; then \
	  ./makefakeasapsym ; \
	else \
	  touch fakeasapsym.sty ; \
	fi

# If we have fontmfizz.sty, generate a faked version that works
# with pdfLaTeX.
FAKEFONTMFIZZ_GEN = \
	fakefontmfizz.sty \
	fakefontmfizz.enc \
	fakefontmfizz.tfm
$(FAKEFONTMFIZZ_GEN) &: makefakelualatex
	if [ "`kpsewhich fontmfizz.sty`" ] ; then \
	  ./makefakelualatex fontmfizz font-mfizz.ttf ; \
	else \
	  touch fakefontmfizz.sty ; \
	fi

# If we have hamnosys.sty, generate a faked version that works
# with pdfLaTeX.
FAKEHAMNOSYS_GEN = \
	fakehamnosys.sty \
	fakehamnosys.enc \
	fakehamnosys.tfm
$(FAKEHAMNOSYS_GEN) &: makefakelualatex
	if [ "`kpsewhich hamnosys.sty`" ] ; then \
	  ./makefakelualatex --regexp='\\DeclareTextCommand\{\\(?P<sym>ham\w+)\}.*?\\char\s*\"(?P<hex>[0-9A-F]+)' hamnosys HamNoSysUnicode.ttf ; \
	else \
	  touch fakehamnosys.sty ; \
	fi

# If we have figchild.sty, generate a faked version that requires fewer TeX
# resources.
fakefigchild.sty: makefakefigchild
	if [ "`kpsewhich figchild.sty`" ] ; then \
	  ./makefakefigchild ; \
	else \
	  touch fakefigchild.sty ; \
	fi

# If we have utfsym.sty, generate a faked version that renders faster.
fakeutfsym.sty: makefakeutfsym
	if [ "`kpsewhich utfsym.sty`" ] ; then \
	  ./makefakeutfsym ; \
	else \
	  touch fakeutfsym.sty ; \
	fi

# If we have logix.sty, generate a faked version that works with pdfLaTeX.
FAKELOGIX_GEN = \
	Logix.pfb \
	fakelogix.sty \
	fakelogixA.enc \
	fakelogixA.tfm \
	fakelogixB.enc \
	fakelogixB.tfm \
	fakelogixC.enc \
	fakelogixC.tfm \
	fakelogixD.enc \
	fakelogixD.tfm \
	fakelogixE.enc \
	fakelogixE.tfm
$(FAKELOGIX_GEN) &: makefakelualatex
	if [ "`kpsewhich logix.sty`" ] ; then \
	  ./makefakelualatex \
	    --regexp='\\newcommand\s*\\(?P<sym>[A-Z]\w+)\s*\{\\lg[lrmx]\{(?P<hex>[0-9A-F]+)\}' \
	    --regexp='\\defineDelimiter\s*\{(?P<sym>[A-Z]\w+)\}\s*\{(?P<hex>[0-9A-F]+)\} ; Big ; 0x2' \
	    logix logix.otf ; \
	else \
	  touch fakelogix.sty ; \
	fi

# Generate a FontForge script that extracts all symbols from a font
# into named, (rather than numbered, as does unicode2eps.pe) EPS
# files.
extract-by-name.pe:
	echo 'Open($$1)' > $@
	echo 'Select(0x0000, 0xFFFF)' >> $@
	echo 'Export("%n.eps")' >> $@

###########################################################################

nonlatex:
	for fname in $(NONLATEX) ; do \
	  $(RM) $$fname ; \
	  fullfname=`kpsewhich $$fname` ; \
	  if [ "$$fullfname" ] ; then \
	    ln -s -f $$fullfname . ; \
	  fi \
	done
	fullfname=`locate -b '\endofproofwd.pdf'` ; \
	if [ "$$fullfname" ] ; then \
	  ln -s -f $$fullfname . ; \
	fi

###########################################################################

# Create a list of all symbols.  We arbitrarily choose the index from the
# U.S. Letter-sized document to count symbols.
SYMLIST: symbols-letter-full.ind
	cat symbols-letter-full.ind | \
	  perl -ne 's/.*\\(?:sp)?verb\+([^+]+)\+.*/$$1/g && print' | \
	  sort -u > SYMLIST

# Create a README file.  We arbitrarily choose the index from the
# U.S. Letter-sized document to count symbols.
README: makeREADME symbols-letter.log symbols-letter-full.ind
	./makeREADME symbols-letter.log symbols-letter-full.ind > README

# Prepare to timestamp the distributed symbols.tex file.
TODAY = $(shell date +'%d %B %Y')
NOW = $(shell date +'%T %Z')

# Create a .tar.gz file.
comprehensive.tar.gz: check_version $(TARGETS) $(EXTRADIST)
	$(RM) -r comprehensive
	mkdir comprehensive
	mkdir comprehensive/source
	install -m 664 $(TARGETS) comprehensive
	install -m 664 $(EXTRADIST) comprehensive/source
	cat symbols.tex | \
	  perl -ne 's/(date\s*=\s*)\"[^\"]*\"/$$1\"$(TODAY)\"/; print' | \
	  perl -ne 's/(time\s*=\s*)\"[^\"]*\"/$$1\"$(NOW)\"/; print' | \
	  checksum > comprehensive/source/symbols.tex
	for script in comprehensive/source/make* ; do \
	  chmod 755 "$$script" ; \
	done
	chmod 755 comprehensive/source/patch-idx
	chmod 755 comprehensive/source/prune-idx
	chmod 664 comprehensive/source/symbols.tex
	tar -czf comprehensive.tar.gz comprehensive
	$(RM) -r comprehensive

dist: comprehensive.tar.gz

# Clean up our mess.
clean: mostlyclean
	$(RM) -r comprehensive
	$(RM) $(TARGETS)
	$(RM) $(NONLATEX)
	for fname in $(NONLATEX) ; do \
	  $(RM) `basename $$fname .mf`.*pk ; \
	  $(RM) `basename $$fname .mf`.tfm ; \
	done
	$(RM) comprehensive.tar.gz
	$(RM) -r junicode lilyglyphs figchild utfsym
	$(RM) fakeMnSymbol.sty fakefdsymbol.sty fakeknitting.sty
	$(RM) fakeboisik.sty fakestix.sty fakestarfont.sty fakecmupint.sty
	$(RM) fakeworldflags.sty fakefigchild.sty fakeutfsym.sty
	$(RM) $(FAKEACADEMICONS_GEN)
	$(RM) $(FAKETYPICONS_GEN)
	$(RM) $(FAKEASAPSYM_GEN)
	$(RM) $(FAKEFONTMFIZZ_GEN)
	$(RM) $(FAKEHAMNOSYS_GEN)
	$(RM) $(FAKELOGIX_GEN)
	$(RM) versatim.tex extract-by-name.pe
	$(RM) mfplain.log
	$(RM) lightbulb10.*pk lightbulb10.{afm,log,pe,pfb,tfm}
	$(RM) lightbulb.{eps,map,pdf}
	$(RM) title-letter.tex title-a4.tex

# Remove just the document itself and intermediate files used in the
# creation of faked packages.
mostlyclean:
	$(RM) symbols-letter-full.ind symbols-a4-full.ind
	$(RM) symbols*.{aux,dep,dvi,fmt,idx,ilg,inc,ind,log,out,pdf,pts,toc}
	$(RM) rawtables-*.{log,tex,pdf} rawtables-letter.list rawtables-a4.list
	$(RM) testfont-letter.{log,pdf} testfont-a4.{log,pdf}
	for dir in worldflags utfsym figchild ; do \
	  $(RM) $$dir/*.log $$dir/*.aux $$dir/*.tex $$dir/mylatex.fmt ; \
	done

.PHONY: all symbols fast-symbols check_version nonlatex dist clean mostlyclean
