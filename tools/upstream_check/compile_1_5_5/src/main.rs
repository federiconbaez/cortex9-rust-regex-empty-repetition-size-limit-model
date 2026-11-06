// Compiles each stdin line "pattern<TAB>size_limit" with the pinned regex crate
// and prints only Ok / the error kind. No input text is ever matched.
use std::io::BufRead;
fn main() {
    for line in std::io::stdin().lock().lines() {
        let line = line.unwrap();
        let mut it = line.split('\t');
        let (p, lim): (&str, usize) = (it.next().unwrap(), it.next().unwrap().parse().unwrap());
        let r = regex::RegexBuilder::new(p).size_limit(lim).build();
        let st = match r {
            Ok(_) => "OK".to_string(),
            Err(regex::Error::CompiledTooBig(n)) => format!("COMPILED_TOO_BIG({})", n),
            Err(e) => format!("ERR {:?}", e),
        };
        println!("{}\t{}\t{}", p, lim, st);
    }
}
