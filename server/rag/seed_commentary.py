"""Seed denomination-tagged commentary snippets bundled with the app.

These are short, original paraphrased summaries (not verbatim quotes) of
mainstream denominational positions, written for the demo. They are tagged so
the retriever can filter by denomination preference while still allowing a
"compare traditions" view.

For a production system this would be a much larger corpus of public-domain
commentaries (Matthew Henry, Catechism CCC excerpts under fair-use, etc.),
ingested from disk during the same recursive-chunking pipeline.
"""
from __future__ import annotations

from typing import List, TypedDict


class CommentaryDoc(TypedDict):
    id: str
    title: str
    denomination: str  # 'protestant' | 'catholic' | 'orthodox' | 'shared'
    source: str
    text: str


SEED: List[CommentaryDoc] = [
    {
        "id": "shared-salvation-overview",
        "title": "Salvation in Christ - shared Christian teaching",
        "denomination": "shared",
        "source": "Demo seed commentary",
        "text": (
            "All mainstream Christian traditions affirm that salvation is made possible "
            "through Jesus Christ, who is fully God and fully human, crucified for the sins "
            "of the world and raised on the third day. The Apostles' Creed and the Nicene "
            "Creed summarize this shared confession. While traditions differ on the precise "
            "relationship between faith, grace, sacraments, and works, the centrality of "
            "Christ's atoning death and bodily resurrection is held in common by Catholic, "
            "Orthodox, and Protestant Christians alike."
        ),
    },
    {
        "id": "protestant-sola-fide",
        "title": "Justification by faith alone (sola fide)",
        "denomination": "protestant",
        "source": "Demo seed commentary (Reformation tradition)",
        "text": (
            "Protestant teaching, rooted in the Reformation, holds that a person is "
            "justified before God by grace alone through faith alone, on account of Christ "
            "alone. Key passages include Romans 3:28, Romans 4:5, Galatians 2:16, and "
            "Ephesians 2:8-9. Good works are understood as the fruit of saving faith, not "
            "its meritorious cause. The Westminster Confession and the Augsburg Confession "
            "articulate this in more detail."
        ),
    },
    {
        "id": "protestant-sola-scriptura",
        "title": "Scripture alone (sola scriptura)",
        "denomination": "protestant",
        "source": "Demo seed commentary (Reformation tradition)",
        "text": (
            "Protestants hold that the Bible is the supreme and final authority for "
            "Christian faith and practice. Tradition, councils, and church leaders are "
            "respected and useful, but always subject to correction by Scripture. "
            "2 Timothy 3:16-17 is a central text. This does not mean Scripture is the only "
            "source of truth, but that it is the only infallible rule of faith."
        ),
    },
    {
        "id": "catholic-sacraments",
        "title": "The seven sacraments",
        "denomination": "catholic",
        "source": "Demo seed commentary (Catholic tradition)",
        "text": (
            "The Catholic Church teaches seven sacraments instituted by Christ and "
            "entrusted to the Church: Baptism, Confirmation, the Eucharist, Reconciliation "
            "(Confession), Anointing of the Sick, Holy Orders, and Matrimony. The Catechism "
            "of the Catholic Church (CCC 1113-1134) describes them as efficacious signs of "
            "grace. The Eucharist is understood as the real presence of the body, blood, "
            "soul, and divinity of Christ under the appearances of bread and wine "
            "(transubstantiation)."
        ),
    },
    {
        "id": "catholic-faith-and-works",
        "title": "Faith and works in Catholic teaching",
        "denomination": "catholic",
        "source": "Demo seed commentary (Catholic tradition)",
        "text": (
            "Catholic teaching holds that justification is by grace through faith, but that "
            "saving faith is necessarily living and active in love (James 2:17, Galatians "
            "5:6). Initial justification is received in Baptism as a free gift; subsequent "
            "growth in grace cooperates with God's grace through faith working in love. The "
            "Council of Trent and the 1999 Joint Declaration on the Doctrine of "
            "Justification clarify this teaching in dialogue with Lutherans."
        ),
    },
    {
        "id": "orthodox-theosis",
        "title": "Theosis (deification) in Orthodox teaching",
        "denomination": "orthodox",
        "source": "Demo seed commentary (Eastern Orthodox tradition)",
        "text": (
            "Eastern Orthodox theology emphasizes salvation as theosis: union with God by "
            "grace, becoming partakers of the divine nature (2 Peter 1:4). This is not "
            "becoming God by essence, but sharing in God's energies through Christ and the "
            "Holy Spirit. The Fathers, especially Athanasius and Maximus the Confessor, "
            "develop this theme. Liturgy, the sacraments (called Holy Mysteries), prayer, "
            "and ascetic life are means by which this transformation unfolds."
        ),
    },
    {
        "id": "orthodox-icons",
        "title": "Icons and the Seventh Ecumenical Council",
        "denomination": "orthodox",
        "source": "Demo seed commentary (Eastern Orthodox tradition)",
        "text": (
            "The Seventh Ecumenical Council (Nicaea II, 787 AD) affirmed the veneration "
            "(not worship) of icons, distinguishing latria (worship due to God alone) from "
            "proskynesis (honor) given to images of Christ, the Theotokos, and the saints. "
            "Because the Word became flesh (John 1:14), the invisible God has made himself "
            "visible in Christ, and so icons of Christ are theologically appropriate."
        ),
    },
    {
        "id": "shared-trinity",
        "title": "The doctrine of the Trinity",
        "denomination": "shared",
        "source": "Demo seed commentary (Nicene tradition)",
        "text": (
            "The Nicene Creed (325/381 AD) confesses one God in three persons: Father, Son, "
            "and Holy Spirit, of one essence (homoousios). This is affirmed by Catholic, "
            "Orthodox, and the vast majority of Protestant traditions. Key biblical "
            "passages include Matthew 28:19, 2 Corinthians 13:14, and John 1:1-14. The "
            "doctrine guards both the unity of God and the full divinity of the Son and "
            "Spirit."
        ),
    },
    {
        "id": "shared-resurrection",
        "title": "The bodily resurrection of Jesus",
        "denomination": "shared",
        "source": "Demo seed commentary",
        "text": (
            "All historic Christian traditions confess the bodily resurrection of Jesus "
            "Christ on the third day, as recounted in Matthew 28, Mark 16, Luke 24, John "
            "20-21, and summarized as central to the gospel in 1 Corinthians 15:3-8. The "
            "resurrection is the vindication of Christ's identity and the ground of "
            "Christian hope for our own resurrection."
        ),
    },
    {
        "id": "shared-difficult-questions",
        "title": "Pastoral approach to difficult questions",
        "denomination": "shared",
        "source": "Demo seed pastoral guidance",
        "text": (
            "When facing hard theological questions - suffering, evil, hell, providence, "
            "predestination - mainstream Christian teaching encourages humility, attention "
            "to the full witness of Scripture, the historic creeds, and the company of the "
            "church. Different traditions emphasize different aspects. A faithful answer "
            "acknowledges mystery where Scripture is silent and avoids false certainty on "
            "contested points."
        ),
    },
]
