// Standalone copy of the Inst type layout from regex b92ffd5 src/prog.rs (no regex crate).
#![allow(dead_code)]
type InstPtr = usize;
enum EmptyLook { StartLine, EndLine, StartText, EndText, WordBoundary, NotWordBoundary, WordBoundaryAscii, NotWordBoundaryAscii }
struct InstSave { goto: InstPtr, slot: usize }
struct InstSplit { goto1: InstPtr, goto2: InstPtr }
struct InstEmptyLook { goto: InstPtr, look: EmptyLook }
struct InstChar { goto: InstPtr, c: char }
struct InstRanges { goto: InstPtr, ranges: Box<[(char, char)]> }
struct InstBytes { goto: InstPtr, start: u8, end: u8 }
enum Inst { Match(usize), Save(InstSave), Split(InstSplit), EmptyLook(InstEmptyLook), Char(InstChar), Ranges(InstRanges), Bytes(InstBytes) }
fn main() { println!("size_of::<Inst>() = {} on {}-bit", std::mem::size_of::<Inst>(), std::mem::size_of::<usize>() * 8); }
