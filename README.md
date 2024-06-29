# Continuing with
Continuing with my [Binary Golf](https://binary.golf) adventure for year 5, I've decided to try and create the smallest Java class that downloads and presents the file.  
Some conclusions from my [Linux shellcode blogpost](https://github.com/yo-yo-yo-jbo/bggp5_linux_shellcode/):
1. Running `curl` is fair game and saves a lot of file size.
2. Short URLs are fair game, and the shortest I found was `7f.uk`.

With that, let's begin!

## Naive Java code
The first thing I did was just compile a simple `java` class with no debugging information:

```java
public class a {
    public static void main(String[] x) throws Exception {
        ProcessBuilder p = new ProcessBuilder("curl", "-L", "7f.uk");
        p.inheritIO();
        p.start();
    }
}
```

Remarks:
- Note the class name is `a` (as the class name is preserved in the Java class).
- We need to decalre `Exception` might be thrown (due to `p.start()`.
- I had to call `p.inheritIO()` for the newly created process to use the current process's `stdout`.
- Normally you're supposed to wait until the process finishes, but I found it okay to just run it - the Java process ends but the new process still finishes a bit later, which is okay according to the rules of the game I guess.

Compiling with `javac -g:none a.java` produces a class of `446` bytes:

```
00000000│cafe babe 0000 003d│0023 0a00 0200 0307│.......=.#......
00000010│0004 0c00 0500 0601│0010 6a61 7661 2f6c│..........java/l
00000020│616e 672f 4f62 6a65│6374 0100 063c 696e│ang/Object...<in
00000030│6974 3e01 0003 2829│5607 0008 0100 186a│it>...()V......j
00000040│6176 612f 6c61 6e67│2f50 726f 6365 7373│ava/lang/Process
00000050│4275 696c 6465 7207│000a 0100 106a 6176│Builder......jav
00000060│612f 6c61 6e67 2f53│7472 696e 6708 000c│a/lang/String...
00000070│0100 0463 7572 6c08│000e 0100 022d 4c08│...curl......-L.
00000080│0010 0100 0537 662e│756b 0a00 0700 120c│.....7f.uk......
00000090│0005 0013 0100 1628│5b4c 6a61 7661 2f6c│.......([Ljava/l
000000a0│616e 672f 5374 7269│6e67 3b29 560a 0007│ang/String;)V...
000000b0│0015 0c00 1600 1701│0009 696e 6865 7269│..........inheri
000000c0│7449 4f01 001c 2829│4c6a 6176 612f 6c61│tIO...()Ljava/la
000000d0│6e67 2f50 726f 6365│7373 4275 696c 6465│ng/ProcessBuilde
000000e0│723b 0a00 0700 190c│001a 001b 0100 0573│r;.............s
000000f0│7461 7274 0100 1528│294c 6a61 7661 2f6c│tart...()Ljava/l
00000100│616e 672f 5072 6f63│6573 733b 0700 1d01│ang/Process;....
00000110│0001 6101 0004 436f│6465 0100 046d 6169│..a...Code...mai
00000120│6e01 000a 4578 6365│7074 696f 6e73 0700│n...Exceptions..
00000130│2201 0013 6a61 7661│2f6c 616e 672f 4578│"...java/lang/Ex
00000140│6365 7074 696f 6e00│2100 1c00 0200 0000│ception.!.......
00000150│0000 0200 0100 0500│0600 0100 1e00 0000│................
00000160│1100 0100 0100 0000│052a b700 01b1 0000│.........*......
00000170│0000 0009 001f 0013│0002 001e 0000 0032│...............2
00000180│0006 0002 0000 0026│bb00 0759 06bd 0009│.......&...Y....
00000190│5903 120b 5359 0412│0d53 5905 120f 53b7│Y...SY...SY...S.
000001a0│0011 4c2b b600 1457│2bb6 0018 57b1 0000│..L+...W+...W...
000001b0│0000 0020 0000 0004│0001 0021 0000     │... .......!..
```

Now is the time to start trimming some unnecessary things, including some strings that might be easily trimmed (e.g. `java/lang/Exception`). This kind of forces me to dive into `class` file format!

## The Java class format
The Java class format is quite simple and very well documented [here](https://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html).  
Without going into too many details, the format is quite simple:
- A simple *header* exists that has a magic value, as well as the major and minor versions.
- Then, there's a *constant pool in the form of number of entries and then the entries themselves. Each entry has a *tag* (type) and its data, which is determined by the type. There are 14 supported types, and they aren't terrible to parse.
- Then we have 3 other simple fields: the class's *access flags*, followed by an index that should point to a descriptor of the class (in the constant pool) and an index that points to the superclass.
- Finally, we have *interfaces*, *fields*, *methods* and *attributes*. All of them are simple arrays, and most of them use indices that point to the constant pool.

It took me around an hour to code my own Java class parser and I share it in this repository.



