# Binary Golf and Java classes
Continuing with my [Binary Golf](https://binary.golf) adventure for year 5, I've decided to try and create the smallest Java class that downloads and presents the data downloaded from the Binary Golf website.  
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
- Everything is Big-Endian (yikes!)
- A simple *header* exists that has a magic value, as well as the major and minor versions.
- Then, there's a *constant pool in the form of number of entries and then the entries themselves. Each entry has a *tag* (type) and its data, which is determined by the type. There are 14 supported types, and they aren't terrible to parse.
- Then we have 3 other simple fields: the class's *access flags*, followed by an index that should point to a descriptor of the class (in the constant pool) and an index that points to the superclass.
- Finally, we have *interfaces*, *fields*, *methods* and *attributes*. All of them are simple arrays, and most of them use indices that point to the constant pool.

It took me around an hour to code my own Java class parser and I share it in this repository.  
Let us run it and parse the header:

```shell
$ ./java_fmt.py ./a.class
MENU
FILE: a.class
[H]eader
[C]onstant pool (34)
[Interfaces (0)
[F]ields (0)
[M]ethods (2)
[A]ttributes (0)
[Q]uit
> H

HEADER
version_minor = 0
major = 61
access_flags = 33
this_class_index (28) -->
  tag = CONSTANT_Class
  name_index (29) -->
    tag = CONSTANT_Utf8
    data = a
super_class_index (2) -->
  tag = CONSTANT_Class
  name_index (4) -->
    tag = CONSTANT_Utf8
    data = java/lang/Object
```

That's quite interesting! We see how the constant pool is used, for instance:
- The `this_class_index` member has a value of `28`, which points to the `27`th member of the constant pool.
- The `27`th item in the constant pool has a tag of type `CONSTANT_Class`, which makes sense since this should be a class descriptor.
- The class descriptor has a `name_index` with the value of `29`, thus pointing to the `28`th member of the constant pool.
- The `28`th item in the constant pool is of type `CONSTANT_Utf8` and has the data `a` in it. UTF-8 strings are simply Pascal-strings (`length` followed by `data` with no NUL terminators).
- Similarly, the `super_class_index` is `2` and points to item `1` in the constant pool, which is a class descriptor that has a name index that eventually points to a UTF-8 string of `java/lang/Object`.

Already several ideas come to mind:
1. How will the JVM treat a descriptor that points to a tag that does not have the type `CONSTANT_Class`? If ignored, we might reuse entries in the constant pool.
2. Can we do an out-of-bounds in one of the indices?
3. Can we call our class `curl`, thus reusing the (expected) `curl` string in the constant pool?

Let's keep all those ideas in our minds, while we print out our methods:

```shell
METHODS
access_flags = 1
name_index (5) -->
  tag = CONSTANT_Utf8
  data = <init>
descriptor_index (6) -->
  tag = CONSTANT_Utf8
  data = ()V
attributes: [
  attribute_name_index (30) -->
    tag = CONSTANT_Utf8
    data = Code
  data = 00 01 00 01 00 00 00 05 2a b7 00 01 b1 00 00 00 00
]
access_flags = 9
name_index (31) -->
  tag = CONSTANT_Utf8
  data = main
descriptor_index (19) -->
  tag = CONSTANT_Utf8
  data = ([Ljava/lang/String;)V
attributes: [
  attribute_name_index (30) -->
    tag = CONSTANT_Utf8
    data = Code
  data = 00 06 00 02 00 00 00 26 bb 00 07 59 06 bd 00 09 59 03 12 0b 53 59 04 12 0d 53 59 05 12 0f 53 b7 00 11 4c 2b b6 00 14 57 2b b6 00 18 57 b1 00 00 00 00
  attribute_name_index (32) -->
    tag = CONSTANT_Utf8
    data = Exceptions
  data = 00 01 00 21
]
```

Interestingly, we have 2 methods!
- One method is called `<init>` and gets no argument and returns `void` (this is the `()V` part). That is a constructor to our class, with very minimal code.
- The other method is our `main` method that gets an array of strings (`[Ljava/lang/String;`) and returns nothing.
- Our `<init>` method has one attribute called `Code` and then the bytecode (which I didn't parse here).
- Our `main` method has a similar `Code` attribute, but also has another attribute called `Exceptions`, which probably declares the fact our method might throw exceptions.

New ideas come to mind:
1. Is the `<init>` method necessary? Also, what does its code do? Can we trim it?
2. Can we simply omit the `Exceptions` attribute from `main`?
3. Will our JVM be able to run `main` that does not accept any arguments?
4. Can we move our entire logic to `<init>`?

For that, we need to run some experiments.

## Experimentation
Some of the easiest experiments do not involve any serious hacking:
1. We can indeed name our class `curl`, and it saves `4` bytes in total, as `javac` repurposes the `curl` string constant and uses it twice (once for the class name, once for the string used in the code).
2. We cannot get rid of `main` method, as the JVM complains if it doesn't find the *exact* `main` method that gets an array of `String`s.

Now, let's get to the harder questions:

### Getting rid of the constructor
You *can* get rid of the `<init>` method, but it'd bite you back later. Removing it completely completely results in this:

```
Error: Unable to initialize main class curl
Caused by: java.lang.VerifyError: Bad invokespecial instruction: current class isn't assignable to reference class.
Exception Details:
  Location:
    curl.main([Ljava/lang/String;)V @23: invokespecial
  Reason:
    Error exists in the bytecode
  Bytecode:
    0000000: bb00 0759 06bd 0009 5903 120b 5359 0412
    0000010: 0d53 5905 120f 53b7 0011 4c2b b600 1457
    0000020: 2bb6 0018 57b1
```

The `invoke-special` instruction is `0xb7`, and it means to run an `instance` method, which is a bit different than running `virtual` methods (which is the default behavior in Java).  
One other idea we could do is move everything to a new method called `<clinit>`, which is the static constructor, that runs when the class gets loaded. This can even be done without any binary patching:

```java
public class curl {
    static {
        ProcessBuilder p = new ProcessBuilder("curl", "-L", "7f.uk");
        p.inheritIO();
        try {
            p.start();
        }
        catch (Exception e) {}
    }
}
```

Unfortunately, this doesn't run, as the JVM refuses to run without a proper `main` method.  
Adding a `main` method that doesn't do anything creates a larger binary, as we now have 3 methods: `<clinit>`, `<init>` an `main`, which results in a larger constant pool.  
As for patching `<init>`, I didn't talk too much about the bytecode itself, but there's a good reference [here](https://en.wikipedia.org/wiki/List_of_Java_bytecode_instructions). I tried patching its first instruction to be `0xb1` (which is `return-void`) but the JVM complains about not initializing the superclass:

```
Error: Unable to initialize main class curl
Caused by: java.lang.VerifyError: Constructor must call super() or this() before return
Exception Details:
  Location:
    curl.<init>()V @0: return
  Reason:
    Error exists in the bytecode
  Bytecode:
    0000000: b1b7 0001 b1
```

Indeed it looks like the JVM verifier validates the constructor initializes the superclass. Since the total code length of `<init>` is 5 bytes, it cannot be improved further.
