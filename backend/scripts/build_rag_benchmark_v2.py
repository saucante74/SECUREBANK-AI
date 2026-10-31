import json
from pathlib import Path

SOURCE_PATH = Path(__file__).resolve().parents[1] / "data" / "rag_benchmark.json"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "rag_benchmark_v2.json"

DOMAIN_GUIDANCE = {
    "mortgage": (
        "Le parcours commence généralement par la définition du projet, puis par "
        "l'examen du budget, des justificatifs et des caractéristiques du bien. La "
        "banque distingue la simulation indicative, l'étude du dossier et la décision "
        "finale. Le client compare le coût global, la souplesse du contrat et les "
        "risques liés à une évolution de sa situation. Une modification du montant, "
        "de la durée, du taux ou de la garantie peut changer l'équilibre du projet."
    ),
    "consumer": (
        "Le financement doit être rapproché du besoin réel, de la durée d'utilisation "
        "du bien et de la capacité mensuelle disponible. Avant de signer, le client "
        "compare montant versé, échéancier, coût total, facultés de remboursement et "
        "conséquences d'un incident. Un crédit ne crée pas une ressource durable : son "
        "remboursement doit rester compatible avec les charges essentielles et les "
        "autres engagements déjà souscrits."
    ),
    "insurance": (
        "Une assurance se lit en reliant le risque déclaré, la garantie mobilisable et "
        "les conditions d'indemnisation. La seule survenance d'un dommage ne suffit pas "
        "toujours : l'événement, les biens, la période et les circonstances doivent "
        "entrer dans le contrat. L'assuré conserve les preuves, respecte les démarches "
        "prévues et vérifie franchises, plafonds, délais, exclusions et obligations de "
        "prévention."
    ),
    "savings": (
        "Le choix d'un support part de l'objectif, de l'horizon, du besoin de disponibilité "
        "et de la perte que le client peut réellement absorber. Rendement, liquidité et "
        "sécurité ne progressent pas nécessairement ensemble. Il faut distinguer dépôt, "
        "placement de marché et enveloppe de détention, puis examiner les frais, les "
        "conditions de sortie et l'absence éventuelle de garantie du capital. La "
        "diversification réduit certains risques sans les supprimer."
    ),
    "payments": (
        "La gestion d'un moyen de paiement repose sur des contrôles simples : vérifier "
        "le bénéficiaire, relire le montant, protéger les accès et consulter les relevés. "
        "Une opération future, une opération déjà comptabilisée et une instruction "
        "récurrente appellent des démarches différentes. Le client agit rapidement, "
        "utilise un canal officiel, conserve les références et distingue blocage, "
        "contestation, rappel et révocation."
    ),
    "security": (
        "La sécurité bancaire combine vigilance du client et contrôles techniques. Une "
        "identité affichée, une connaissance partielle du dossier ou une validation forte "
        "ne prouvent pas à elles seules la légitimité d'une demande. Le client interrompt "
        "l'échange douteux, revient vers un canal obtenu indépendamment et ne communique "
        "ni secret ni validation. En cas d'incident, la rapidité du signalement améliore "
        "les possibilités de protection sans garantir la récupération des fonds."
    ),
    "compliance": (
        "La relation bancaire nécessite des informations cohérentes et actualisées sur "
        "l'identité, l'activité, la résidence fiscale et l'origine économique de certaines "
        "opérations. La demande dépend du contexte et ne signifie pas, à elle seule, "
        "qu'une irrégularité existe. Le client transmet seulement les pièces demandées "
        "par un canal vérifié. La banque peut poser des questions complémentaires lorsque "
        "les informations reçues ne suffisent pas à comprendre la situation."
    ),
}

DOMAIN_EXAMPLES = {
    "mortgage": "Un ménage compare deux scénarios de logement et conserve une marge pour les dépenses imprévues avant de choisir une durée de financement.",
    "consumer": "Une personne chiffre son projet, vérifie son budget après charges essentielles et compare un prêt amortissable avec les autres solutions disponibles.",
    "insurance": "Après un événement, l'assuré sécurise les lieux, documente les dommages et relit son contrat avant d'engager une réparation définitive non urgente.",
    "savings": "Une personne sépare sa réserve disponible d'une somme destinée à un projet lointain, puis choisit des supports adaptés à chaque horizon.",
    "payments": "Un client constate une opération inhabituelle, vérifie son libellé, contacte la banque par l'application officielle et conserve la référence de sa démarche.",
    "security": "Un appelant demande une action urgente ; le client raccroche, retrouve lui-même le numéro officiel et vérifie la situation avant toute validation.",
    "compliance": "À la réception de fonds liés à une vente, le client prépare les pièces décrivant l'opération et les transmet uniquement dans l'espace sécurisé indiqué.",
}


def document_domain(document_id: str) -> str:
    if document_id.startswith("benchmark-mortgage-"):
        return "mortgage"
    if document_id.startswith("benchmark-consumer-"):
        return "consumer"
    if document_id.startswith("benchmark-insurance-"):
        return "insurance"
    if document_id.startswith("benchmark-savings-"):
        return "savings"
    if document_id.startswith("benchmark-payments-"):
        return "payments"
    if document_id.startswith("benchmark-security-"):
        return "security"
    if document_id.startswith("benchmark-compliance-"):
        return "compliance"
    raise ValueError(f"unknown document domain for {document_id!r}")


def enrich_content(document_id: str, original_content: str) -> str:
    domain = document_domain(document_id)
    return "\n\n".join(
        (
            "Cadre du document\nCe document bancaire est entièrement synthétique et "
            "destiné à un prototype pédagogique. Il ne constitue ni un conseil "
            "personnalisé, ni une offre contractuelle, ni une description exhaustive "
            "du droit applicable. Les conditions réelles dépendent du contrat, de "
            "l'établissement et de la situation du client. Tout montant, seuil, délai, "
            "taux ou frais utilisé dans un exemple doit être compris comme fictif.",
            f"Informations essentielles conservées\n{original_content}",
            f"Fonctionnement pratique\n{DOMAIN_GUIDANCE[domain]}",
            "Conditions et préparation\nLe client commence par identifier son besoin, "
            "rassembler les documents utiles et vérifier que les informations fournies "
            "sont exactes et à jour. Il demande une explication lorsqu'un terme, un coût "
            "ou une conséquence n'est pas clair. Les échanges importants sont conservés "
            "avec leur date et leur référence. Les documents sensibles sont transmis par "
            "le canal sécurisé annoncé par la banque, après vérification indépendante de "
            "l'identité du destinataire. Une simulation ou un exemple ne remplace jamais "
            "la lecture des conditions particulières et générales.",
            "Limites et cas particuliers\nUne réponse standard peut devenir inadaptée "
            "si plusieurs titulaires sont concernés, si une opération est internationale, "
            "si le client agit pour une entreprise, si sa situation financière change ou "
            "si un incident est déjà survenu. Les délais de traitement et les pièces "
            "demandées peuvent varier selon le dossier. Une décision peut nécessiter un "
            "contrôle complémentaire. En présence d'une urgence, le client protège d'abord "
            "les personnes et les accès, puis contacte l'interlocuteur compétent. Aucune "
            "procédure décrite ici ne garantit une acceptation, une indemnisation, un "
            "remboursement ou une performance.",
            f"Exemple synthétique\n{DOMAIN_EXAMPLES[domain]} Cet exemple illustre une "
            "démarche de vérification et non une règle universelle. La personne compare "
            "les documents disponibles, note les hypothèses, identifie les risques et "
            "demande une confirmation écrite avant de s'engager.",
            "Points de contrôle\nAvant de conclure, le client vérifie l'objectif, les "
            "conditions d'entrée et de sortie, les coûts annoncés, les risques, les "
            "exceptions, les justificatifs et le canal de contact. Il distingue ce qui "
            "est certain de ce qui reste indicatif. Si les informations sont insuffisantes "
            "ou contradictoires, il suspend sa décision jusqu'à clarification.",
        )
    )


def main() -> int:
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    documents = [
        {
            **document,
            "content": enrich_content(document["id"], document["content"]),
        }
        for document in source["documents"]
    ]
    reference_questions = [
        {
            "id": case["id"],
            "question": case["question"],
            "difficulty": case["difficulty"],
            "rationale": case["rationale"],
        }
        for case in source["cases"]
    ]
    word_counts = [len(document["content"].split()) for document in documents]
    if len(documents) != 30 or len(reference_questions) != 40:
        raise ValueError("unexpected source dataset size")
    if not all(300 <= count <= 600 for count in word_counts):
        raise ValueError("enriched documents must contain 300 to 600 words")
    payload = {
        "schema_version": 2,
        "source_dataset": "rag_benchmark.json",
        "annotation_status": "unannotated",
        "documents": documents,
        "reference_questions": reference_questions,
    }
    with OUTPUT_PATH.open("x", encoding="utf-8") as output_file:
        json.dump(payload, output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")
    print(f"Corpus v2 saved: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
