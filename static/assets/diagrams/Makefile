OPTIONS=-Gfontname=helvetica -Gfontsize=14 -Nfontname=helvetica -Nfontsize=14 -Efontname=helvetica -Efontsize=14 -Gbgcolor=transparent

all: $(patsubst %.dot,%.png, $(wildcard *.dot))

%.png: %.dot
	dot $(OPTIONS) -Tpng -o$@ $^

clean:
	rm *.png


