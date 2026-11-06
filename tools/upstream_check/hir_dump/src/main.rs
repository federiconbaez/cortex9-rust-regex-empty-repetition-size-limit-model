// Prints the HIR that regex-syntax 0.6.25 builds for each stdin line, as a
// compact S-expression. Parser only: nothing is compiled or matched.
use regex_syntax::hir::{self, Hir, HirKind, RepetitionKind, RepetitionRange};
use regex_syntax::ParserBuilder;
use std::io::BufRead;

fn s(h: &Hir) -> String {
    match h.kind() {
        HirKind::Empty => "Empty".into(),
        HirKind::Literal(hir::Literal::Unicode(c)) => format!("Lit({})", c),
        HirKind::Literal(hir::Literal::Byte(b)) => format!("Byte({})", b),
        HirKind::Anchor(a) => format!("Anchor({:?})", a),
        HirKind::Class(_) => "Class".into(),
        HirKind::WordBoundary(_) => "WordBoundary".into(),
        HirKind::Group(g) => {
            let k = match &g.kind {
                hir::GroupKind::NonCapturing => "NC".to_string(),
                hir::GroupKind::CaptureIndex(i) => format!("Cap{}", i),
                hir::GroupKind::CaptureName { index, .. } => format!("Cap{}", index),
            };
            format!("Group({},{})", k, s(&g.hir))
        }
        HirKind::Repetition(r) => {
            let (k, min, max) = match &r.kind {
                RepetitionKind::ZeroOrOne => ("ZeroOrOne", 0, Some(1)),
                RepetitionKind::ZeroOrMore => ("ZeroOrMore", 0, None),
                RepetitionKind::OneOrMore => ("OneOrMore", 1, None),
                RepetitionKind::Range(RepetitionRange::Exactly(n)) => ("Exactly", *n, Some(*n)),
                RepetitionKind::Range(RepetitionRange::AtLeast(n)) => ("AtLeast", *n, None),
                RepetitionKind::Range(RepetitionRange::Bounded(a, b)) => ("Bounded", *a, Some(*b)),
            };
            let max = max.map(|m| m.to_string()).unwrap_or_else(|| "inf".into());
            format!(
                "Rep({},{},{},{},{})",
                k,
                min,
                max,
                if r.greedy { "g" } else { "l" },
                s(&r.hir)
            )
        }
        HirKind::Concat(v) => format!("Concat({})", v.iter().map(s).collect::<Vec<_>>().join(",")),
        HirKind::Alternation(v) => {
            format!("Alt({})", v.iter().map(s).collect::<Vec<_>>().join(","))
        }
    }
}

fn main() {
    for line in std::io::stdin().lock().lines() {
        let p = line.unwrap();
        // regex 1.5.4 re_builder.rs: ParserBuilder with nest_limit 250, unicode true, rest false
        let r = ParserBuilder::new()
            .nest_limit(250)
            .unicode(true)
            .build()
            .parse(&p);
        match r {
            Ok(h) => println!("{}\t{}", p, s(&h)),
            Err(e) => println!("{}\tERR {}", p, e.to_string().lines().last().unwrap_or("")),
        }
    }
}
