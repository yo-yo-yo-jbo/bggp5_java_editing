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
