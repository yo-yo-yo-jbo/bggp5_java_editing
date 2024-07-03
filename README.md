## Binary Golf and Java classes
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
- We need to declare `Exception` might be thrown (due to `p.start()`.
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

### Failed ideas
- I tried using a [URLClassLoader](https://docs.oracle.com/javase/8/docs/api/java/net/URLClassLoader.html) to load further code from some short-form URL I register, but the size turned up to be too big (`457` bytes to be exact).
- I tried inheriting from `ProcessBuilder` to not have a direct reference to `Object` as a superclass, but it didn't work due to `ProcessBuilder` being `final`.
- I thought of incorporating `native` code, but could not find easy ways in `libc.so.6` to make it appear as if we have a JNI method that'd not crash the process.
- At a certain point I thought that the `-L` flag should be omitted at the price of using the entire URL for the Binary Golf download target, but it turns out the short URL with the `-L` flag actually save 5 bytes, so in total you should still use the short URL even at the price of one more constant pool entry.
- The documentation states you could leave a value of `0` (which is kind of `null`) for the index that represents the descriptor of the superclass instead of referring to `java.lang.Object`. That could save a lot of room, but unfortunately the JVM verifier validates this and refuses to run the code.
- Initially I thought using `Runtime.getRuntime.exec` is not a good approach, due to not being able to easily divert the standard output without bloating the code. It took me a while to figure out a neat trick, keep reading!
- I tried just not returning from my code (i.e. removing the `return` bytecode instruction), but the verifier looks for that and refuses to load your code.

## The Java class format
The Java class format is quite simple and very well documented [here](https://docs.oracle.com/javase/specs/jvms/se7/html/jvms-4.html).  
Without going into too many details, the format is quite simple:
- Everything is Big-Endian (yikes!)
- A simple *header* exists that has a magic value, as well as the major and minor versions.
- Then, there's a *constant pool* in the form of number of entries and then the entries themselves. Each entry has a *tag* (type) and its data, which is determined by the type. There are 14 supported types, and they aren't terrible to parse.
- Then we have 3 other simple fields: the class's *access flags*, followed by an index that should point to a descriptor of the class (in the constant pool) and an index that points to the superclass.
- Finally, we have *interfaces*, *fields*, *methods* and *attributes*. All of them are simple arrays, and most of them use indices that point to the constant pool.

It took me around an hour to code my own Java class parser and I share it in this repository (see [java_fmt.py](java_fmt.py)).  
Let us run it and parse the header:

```shell
$ ./java_fmt.py ./a.class
MENU
FILE: a.class
[H]eader
[C]onstant pool (34)
[D]escriptor for the class
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
1. We can indeed name our class `curl`, and it saves `4` bytes in total, as `javac` repurposes the `curl` string constant and uses it twice (once for the class name, once for the string used in the code). The total size reduces to `442` bytes.
2. We cannot get rid of `main` method, as the JVM complains if it doesn't find the *exact* `main` method that gets an array of `String`s.

Now, let's get to the harder questions:

### Can we get rid of the default constructor?
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

### Other experiments
- I've tried checking if the `tag` is really used or we can abuse a type confusion. The JVM I have strongly checks the `tag`.
- Out-of-bounds in the constant pool is a no-go, resulting in verifier failures (if used statically) or crashes (if used in a `Code` attribute).

### Reducing Exceptions references
One more thing left to do: our `main` method has an extra attribute called `Exceptions` and has `4` bytes.  
The format of the `Exceptions` data is simply the number of the exceptions (2-bytes) followed by exception reference numbers (2 bytes each).  
Our bytes are `00 01 00 20`, so we have `1` exception referencing index `0x20` (`32`), and indeed, using my tool we see:

```
CONSTANT POOL (32)
tag = CONSTANT_Class
name_index (33) -->
  tag = CONSTANT_Utf8
  data = java/lang/Exception
```

Additionally, the name `Exceptions` itself is referenced by index `31`. So, our plan is:
- Removing entry `31` from the constant pool (the UTF-8 constant that says `Exceptions`).
- Removing entry `32` from the constant pool (the class descriptor for `Java/lang/Exception`).
- Removing entry `33` from the constant pool (the UTF-8 string for `Java/lang/Exception`).
- Removing the `2`nd attribute from the `2`nd method.

The effect is that it'd be as if we didn't declare `main` to `throw Exception`, which is fine for our execution.  
I've done that work manually with some binary editing, and ended up with the following `390` bytes `curl.class` file... And indeed:

```shell
jbo@McJbo % java curl
jbo@McJbo % Another #BGGP5 download!! @binarygolf https://binary.golf
```

When running with my tool, it looks like this:

```
METHODS
access_flags = 1
name_index (5) -->
  tag = CONSTANT_Utf8
  data = <init>
descriptor_index (6) -->
  tag = CONSTANT_Utf8
  data = ()V
attributes: [
  attribute_name_index (29) -->
    tag = CONSTANT_Utf8
    data = Code
  data = 00 01 00 01 00 00 00 05 2a b7 00 01 b1 00 00 00 00
]
access_flags = 9
name_index (30) -->
  tag = CONSTANT_Utf8
  data = main
descriptor_index (19) -->
  tag = CONSTANT_Utf8
  data = ([Ljava/lang/String;)V
attributes: [
  attribute_name_index (29) -->
    tag = CONSTANT_Utf8
    data = Code
  data = 00 06 00 01 00 00 00 22 bb 00 07 59 06 bd 00 09 59 03 12 0b 53 59 04 12 0d 53 59 05 12 0f 53 b7 00 11 b6 00 14 b6 00 18 57 b1 00 00 00 00
]
```

### Abusing abstract classes and finally getting rid of the constructor
Surprisingly, because `main` is a `static` method, I discovered you could have an `abstract` class that'd still run!

```java
public abstract class curl {
    public static void main(String[] x) throws Exception {
        (new ProcessBuilder("curl", "-L", "7f.uk")).inheritIO().start();
    }
}
```

This runs well, but still generates an `<init>` method... But because the class is `abstract`, it should never be called... Can we omit it?  
Apparently, we can, saving the `<init>` method and all its references in the constant pool (there are `3` of those), as well as removing the `Exception` handling. After patching, I was able to reduce the class to a size of `343` bytes only!

```
00000000│cafe babe 0000 003d│001c 0100 046d 6169│.......=.....mai
00000010│6e07 0004 0100 0443│6f64 6501 0010 6a61│n......Code...ja
00000020│7661 2f6c 616e 672f│4f62 6a65 6374 0100│va/lang/Object..
00000030│063c 696e 6974 3e07│000c 0700 0801 0018│.<init>.........
00000040│6a61 7661 2f6c 616e│672f 5072 6f63 6573│java/lang/Proces
00000050│7342 7569 6c64 6572│0700 0a01 0010 6a61│sBuilder......ja
00000060│7661 2f6c 616e 672f│5374 7269 6e67 0800│va/lang/String..
00000070│0c01 0004 6375 726c│0800 0e01 0002 2d4c│....curl......-L
00000080│0800 1001 0005 3766│2e75 6b0a 0007 0012│......7f.uk.....
00000090│0c00 0500 1301 0016│285b 4c6a 6176 612f│........([Ljava/
000000a0│6c61 6e67 2f53 7472│696e 673b 2956 0a00│lang/String;)V..
000000b0│0700 150c 0016 0017│0100 0969 6e68 6572│...........inher
000000c0│6974 494f 0100 1c28│294c 6a61 7661 2f6c│itIO...()Ljava/l
000000d0│616e 672f 5072 6f63│6573 7342 7569 6c64│ang/ProcessBuild
000000e0│6572 3b0a 0007 0019│0c00 1a00 1b01 0005│er;.............
000000f0│7374 6172 7401 0015│2829 4c6a 6176 612f│start...()Ljava/
00000100│6c61 6e67 2f50 726f│6365 7373 3b04 2100│lang/Process;.!.
00000110│0600 0200 0000 0000│0100 0900 0100 1300│................
00000120│0100 0300 0000 2e00│0600 0100 0000 22bb│..............".
00000130│0007 5906 bd00 0959│0312 0b53 5904 120d│..Y....Y...SY...
00000140│5359 0512 0f53 b700│11b6 0014 b600 1857│SY...S.........W
00000150│b100 0000 0000 00  │                   │.......
```

### Getting rid of Object inheritence
Lastly, our class currently inherits from `Object`, which takes the string `java/lang/Object` in the constant pool.  
I noticed that isn't referenced by anything besides our superclass descriptor. My first thought was to use a different class descriptor, but:
- While the `ProcessBuilder` and `String` classes exist in our constant pool, they are both `final` so the verifier fails for inheriting from them.
- I cannot self-inherit, even though I am an `abstract` class - the verifier fails on these kind of recursive definitions.

I didn't find any other strings that would be usable classes to inherit from, so my goal was to shorten `java/lang/Object` to a shorter class.  
Primitive types or their arrays would be ideal, but they are not available for inheritence, so I ended up checking all builtin classes and find the one with the shortest name: `java/io/File` and others have a total length of `12` characters.
So, replacing that string constant from `java/lang/Object` to `java/io/File` reduces my file size further to `339` bytes:

```
00000000│cafe babe 0000 003d│001c 0100 046d 6169│.......=.....mai
00000010│6e07 0004 0100 0443│6f64 6501 000c 6a61│n......Code...ja
00000020│7661 2f69 6f2f 4669│6c65 0100 063c 696e│va/io/File...<in
00000030│6974 3e07 000c 0700│0801 0018 6a61 7661│it>.........java
00000040│2f6c 616e 672f 5072│6f63 6573 7342 7569│/lang/ProcessBui
00000050│6c64 6572 0700 0a01│0010 6a61 7661 2f6c│lder......java/l
00000060│616e 672f 5374 7269│6e67 0800 0c01 0004│ang/String......
00000070│6375 726c 0800 0e01│0002 2d4c 0800 1001│curl......-L....
00000080│0005 3766 2e75 6b0a│0007 0012 0c00 0500│..7f.uk.........
00000090│1301 0016 285b 4c6a│6176 612f 6c61 6e67│....([Ljava/lang
000000a0│2f53 7472 696e 673b│2956 0a00 0700 150c│/String;)V......
000000b0│0016 0017 0100 0969│6e68 6572 6974 494f│.......inheritIO
000000c0│0100 1c28 294c 6a61│7661 2f6c 616e 672f│...()Ljava/lang/
000000d0│5072 6f63 6573 7342│7569 6c64 6572 3b0a│ProcessBuilder;.
000000e0│0007 0019 0c00 1a00│1b01 0005 7374 6172│............star
000000f0│7401 0015 2829 4c6a│6176 612f 6c61 6e67│t...()Ljava/lang
00000100│2f50 726f 6365 7373│3b04 2100 0600 0200│/Process;.!.....
00000110│0000 0000 0100 0900│0100 1300 0100 0300│................
00000120│0000 2e00 0600 0100│0000 22bb 0007 5906│.........."...Y.
00000130│bd00 0959 0312 0b53│5904 120d 5359 0512│...Y...SY...SY..
00000140│0f53 b700 11b6 0014│b600 1857 b100 0000│.S.........W....
00000150│0000 00            │                   │...
```

### Code optimizations
Now we have only one method - our `main` method. I didn't add the code parsing to my tool, but it's quite easy to do it manually, especially for such short code.  
I am not ashamed to say I used the [Wikipedia page](https://en.wikipedia.org/wiki/List_of_Java_bytecode_instructions) for the Java bytecode instructions.  
The JVM is basically a mix of stack and register machine, so following the instructions is quite easy. Note this is *not* the stack used by the CPU, it's the JVM stack that is implemented 100% in software.  
Anyway, my current code looks like this (annotations were done by me):

```assembly
bb 00 07        new             java/lang/ProcessBuilder (C7)
59              dup
06              iconst_3
bd 00 09        anewarray       java/lang/String (C9)
59              dup
03              iconst_0
12 0b           ldc             "curl" (C11)
53              aastore
59              dup
04              iconst_1
12 0d           ldc             "-L" C(13)
53              aastore
59              dup
05              iconst_2
12 0f           ldc             "7f.uk" (C15)
53              aastore
b7 00 11        invokespecial    java/lang/ProcessBuilder::<init>([Ljava/lang/String;)V (C17)
b6 00 14        invokevirtual    java/lang/ProcessBuilder::inheritIO()Ljava/lang/ProcessBuilder; (C20)
b6 00 18        invokevirtual    java/lang/ProcessBuilder::start()Ljava/lang/Process; (C24)
57              pop
b1              return
```

Let's follow line by line:
1. We create a new `ProcessBuilder`, which is quite necessary for our execution. Note that this allocates that object (but does not initialize it yet!) and pushes it to the stack.
2. We duplicate the value in the stack - we now have two references to the same `ProcessBuilder` instance.
3. We push the constant `3` to the stack.
4. We create a new array of type `String`, with a size of `3` (since `3` was pushed to the stack). The `3` value is popped from the stack and the new array is pushed.
5. We duplicate the last value in the stack, so we now have two references to the `String` array in the stack.
6. We push the value `0` to the stack.
7. We push a reference to the string `curl` to the stack.
8. We store the value `curl` at index `0` to the `String` array - all of those 3 values were popped from the stack and nothing was pushed. That explains the `dup` in line `5` - otherwise we'd lose the reference to the `String` array! Our current stack contains two references to the allocated `ProcessBuilder` followed by a reference to the `String` array, which is in the top of the stack.
9. We duplicate the `String` array reference on the stack, similarly to what we did before.
10. We push the value `1` to the stack.
11. We push a reference to the string `-L` to the stack.
12. We store the value `-L` at index `1` to the `String` array, popping all 3 lastly pushed items from the stack, similarly to line 8.
13. We duplicate the `String` array reference on the stack, similarly to what we did before.
14. We push the value `2` to the stack.
15. We push a reference to the string `7f.uk` to the stack.
16. We store the value `7f.uk` at index `2` to the `String` array, popping all 3 lastly pushed items from the stack, similarly to line 8 and line 12.
17. We call the `StringBuilder`'s constructor (`<init>`) that gets an array of `String`s and the object reference from the stack (unlike what Wikipedia says, it does *not* put anything back on the stack).
18. We call `inheritIO` virtual method on the `ProcessBuilder` instance - the result is pushed back. Since the result of `inheritIO` is exactly the same object instance, nothing is changed on the stack.
19. We call `start` virtual method on the `ProcessBuilder` instance. The resulting `Process` is pushed back to the stack.
20. We call `pop` to remove the returned `Process` instance and basically "ignore" it while cleaning up the stack.
21. We `return` from the method.

It doesn't seem there's a lot of space for optimizations, *besides one thing* - the `pop` instruction at the end is meant to make sure the stack gets cleaned up, but I've discovered that at least in my case, the JVM doesn't care (maybe because my method is the `main` method). Thus, I can save one more byte, reducing my solution to `338` bytes!

```
00000000│cafe babe 0000 003d│001c 0100 046d 6169│.......=.....mai
00000010│6e07 0004 0100 0443│6f64 6501 000c 6a61│n......Code...ja
00000020│7661 2f69 6f2f 4669│6c65 0100 063c 696e│va/io/File...<in
00000030│6974 3e07 000c 0700│0801 0018 6a61 7661│it>.........java
00000040│2f6c 616e 672f 5072│6f63 6573 7342 7569│/lang/ProcessBui
00000050│6c64 6572 0700 0a01│0010 6a61 7661 2f6c│lder......java/l
00000060│616e 672f 5374 7269│6e67 0800 0c01 0004│ang/String......
00000070│6375 726c 0800 0e01│0002 2d4c 0800 1001│curl......-L....
00000080│0005 3766 2e75 6b0a│0007 0012 0c00 0500│..7f.uk.........
00000090│1301 0016 285b 4c6a│6176 612f 6c61 6e67│....([Ljava/lang
000000a0│2f53 7472 696e 673b│2956 0a00 0700 150c│/String;)V......
000000b0│0016 0017 0100 0969│6e68 6572 6974 494f│.......inheritIO
000000c0│0100 1c28 294c 6a61│7661 2f6c 616e 672f│...()Ljava/lang/
000000d0│5072 6f63 6573 7342│7569 6c64 6572 3b0a│ProcessBuilder;.
000000e0│0007 0019 0c00 1a00│1b01 0005 7374 6172│............star
000000f0│7401 0015 2829 4c6a│6176 612f 6c61 6e67│t...()Ljava/lang
00000100│2f50 726f 6365 7373│3b04 2100 0600 0200│/Process;.!.....
00000110│0000 0000 0100 0900│0100 1300 0100 0300│................
00000120│0000 2d00 0600 0100│0000 21bb 0007 5906│..-.......!...Y.
00000130│bd00 0959 0312 0b53│5904 120d 5359 0512│...Y...SY...SY..
00000140│0f53 b700 11b6 0014│b600 18b1 0000 0000│.S..............
00000150│0000               │                   │..
```

## Update - less code with a terminal trick
I've decided to examine the `Runtime.getRuntime().exec()` option - until this point it was not appealing due to the need to divert the standard output which still requires `ProcessBuilder`.  
However, the option became more appealing mostly due to `Runtime` not being `final` - that means my class could inherit from `Runtime` - as long as I can find a trick to divert the standard output.  
So, the challenges I am facing are:
1. As I mentioned, even if your class is `abstract` - the compiler would still try to create a constructor (`<init>`) - and even if you create one yourself, the compiler would make sure to call `super()` on it - and there's no constructor for `Runtime` that gets 0 arguments. I solved that by inheriting from `Object` and patching the class later.
2. Diverting the standard output. I ended up doing a weird trick: `sh -c "curl 7f.uk>/dev/tty` solved the problem - which means my solution wouldn't work on Windows, but I think it's still a cool idea.
3. I still have to remove the `Exception` handling later as `Runtime.exec()` throws.

I've decided to call my class `Code`, which would still re-use the mandatory `Code` string. My base code was this:

```java
public abstract class Code {
    public static void main(String[] args) throws Exception {
        Runtime.getRuntime().exec(new String[] {"sh", "-c", "curl -L 7f.uk>/dev/tty"});
    }
}
```

I've applied all we learned:
1. Removing `Exception` handling in the `main` method's second attribute (called `Exceptions`).
2. Getting rid of `<init>`.
3. Inheriting from `Runtime` rather than `Object`.
4. Removing all unnecessary entries from the constant pool.
5. Removing the last `pop` instruction from our bytecode.

And - success! My class is now only `314` bytes long, and works well!

```
00000000│cafe babe 0000 003d│0017 0a00 0200 0307│.......=........
00000010│0004 0c00 0500 0601│0011 6a61 7661 2f6c│..........java/l
00000020│616e 672f 5275 6e74│696d 6501 000a 6765│ang/Runtime...ge
00000030│7452 756e 7469 6d65│0100 1528 294c 6a61│tRuntime...()Lja
00000040│7661 2f6c 616e 672f│5275 6e74 696d 653b│va/lang/Runtime;
00000050│0700 0801 0010 6a61│7661 2f6c 616e 672f│......java/lang/
00000060│5374 7269 6e67 0800│0a01 0002 7368 0800│String......sh..
00000070│0c01 0002 2d63 0800│0e01 0016 6375 726c│....-c......curl
00000080│202d 4c20 3766 2e75│6b3e 2f64 6576 2f74│ -L 7f.uk>/dev/t
00000090│7479 0a00 0200 100c│0011 0012 0100 0465│ty.............e
000000a0│7865 6301 0028 285b│4c6a 6176 612f 6c61│xec..(([Ljava/la
000000b0│6e67 2f53 7472 696e│673b 294c 6a61 7661│ng/String;)Ljava
000000c0│2f6c 616e 672f 5072│6f63 6573 733b 0700│/lang/Process;..
000000d0│1401 0004 436f 6465│0100 046d 6169 6e01│....Code...main.
000000e0│0016 285b 4c6a 6176│612f 6c61 6e67 2f53│..([Ljava/lang/S
000000f0│7472 696e 673b 2956│0421 0013 0002 0000│tring;)V.!......
00000100│0000 0001 0009 0015│0016 0001 0014 0000│................
00000110│0026 0005 0001 0000│001a b800 0106 bd00│.&..............
00000120│0759 0312 0953 5904│120b 5359 0512 0d53│.Y...SY...SY...S
00000130│b600 0fb1 0000 0000│0000               │..........
```

### Moving to a single string
Some of you might wonder why I haven't used th `exec` method that gets a single string. Well, the reason is that I didn't use it is how Java's implementation works.  
You see, `exec(String)` is a convenience method that would internally just split the string to whitespaces and feed it in an array. Note that I still need to use `>/dev/tty`, so I have to use `sh`.  
My plan was to do the following:

```java
Runtime.getRuntime().exec("sh -c curl -L 7f.uk>/dev/tty");
```

Alas, it'd get split by Java, so the equivalent is this:

```java
Runtime.getRuntime.exec(new String[5] { "sh", "-c", "curl", "-L", "7f.uk>/dev/tty" });
```

This isn't good - I need to work around that. Well, the trick that I found is pretty neat - I use the shell's [parameter expansion](https://www.gnu.org/software/bash/manual/html_node/Shell-Parameter-Expansion.html) (which means I have to use `bash` and not `sh`) to get an existing environment variable with a space in it. Luckily, `$IFS` is literally the variable that I need - it contains all the token-splitters for the commandline.  
Therefore, my goal is running this:

```java
Runtime.getRuntime().exec("bash -c curl${IFS:1:1}-L${IFS:1:1}7f.uk>/d*/tty");
```

Note that I also used `/d*/tty` to shorten `/dev` by one character - neat!
As usual, I applied all the tricks from before - luckily my code is much smaller (bytecode is only `9` bytes now!) and the constant pool has only `16` entries. In total - we are at `283` bytes!  
The bytecode:

```assembly
b8 00 01        invokestatic     java/lang/Runtime::getRuntime()Ljava/lang/Runtime; (C1)
12 02           ldc              "bash -c curl${IFS:1:1}-L${IFS:1:1}7f.uk>/d*/tty" (C2)
b6 00 03        invokevirtual    java/lang/Runtime::exec(Ljava/lang/String;)Ljava/lang/Process; (C3)
b1              return
```

The content:
```
00000000│cafe babe 0000 0037│0011 0a00 0800 0908│.......7........
00000010│000a 0a00 0800 0b07│0005 0100 0443 6f64│.............Cod
00000020│6501 0004 6d61 696e│0100 1628 5b4c 6a61│e...main...([Lja
00000030│7661 2f6c 616e 672f│5374 7269 6e67 3b29│va/lang/String;)
00000040│5607 000c 0c00 0d00│0e01 002f 6261 7368│V........../bash
00000050│202d 6320 6375 726c│247b 4946 533a 313a│ -c curl${IFS:1:
00000060│317d 2d4c 247b 4946│533a 313a 317d 3766│1}-L${IFS:1:1}7f
00000070│2e75 6b3e 2f64 2a2f│7474 790c 000f 0010│.uk>/d*/tty.....
00000080│0100 116a 6176 612f│6c61 6e67 2f52 756e│...java/lang/Run
00000090│7469 6d65 0100 0a67│6574 5275 6e74 696d│time...getRuntim
000000a0│6501 0015 2829 4c6a│6176 612f 6c61 6e67│e...()Ljava/lang
000000b0│2f52 756e 7469 6d65│3b01 0004 6578 6563│/Runtime;...exec
000000c0│0100 2728 4c6a 6176│612f 6c61 6e67 2f53│..'(Ljava/lang/S
000000d0│7472 696e 673b 294c│6a61 7661 2f6c 616e│tring;)Ljava/lan
000000e0│672f 5072 6f63 6573│733b 0421 0004 0008│g/Process;.!....
000000f0│0000 0000 0001 0009│0006 0007 0001 0005│................
00000100│0000 0015 0002 0001│0000 0009 b800 0112│................
00000110│02b6 0003 b100 0000│0000 00            │...........
```

## Summary
All in all, we found good ways of minimizing the class:
1. Implement our class `abstract`, thus getting rid of `<init>` completely.
2. Inheriting from a class different than `Object` - shortest name I could find was `java/io/File` but in the case of `Runtime` I could reuse `Runtime` as a superclass, which is only possible due removing `<init>` entirely.
3. Getting rid of `Exception` handling.
4. Not cleaning up the stack.
5. Re-using strings (e.g. calling your class `Code` or `curl` in our case).
6. Using things like `/dev/tty` to write to the output and substrings of `$IFS` to work-around spaces.

I gotta say, Binary Golf is super fun and makes you learn new things every day!  
I really enjoy the challenge and considering playing some more, maybe with an Android App this time.

Stay tuned!

Jonathan Bar Or

