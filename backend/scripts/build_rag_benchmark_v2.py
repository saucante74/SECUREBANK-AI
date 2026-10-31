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

PILOT_SECTIONS = {
    "benchmark-mortgage-capacity": (
        "Analyse du budget\nLa capacité de remboursement se construit à partir des "
        "revenus réguliers, des charges récurrentes, des crédits en cours et du reste "
        "disponible après les dépenses essentielles. Le taux d'effort est un indicateur "
        "d'analyse, mais la banque examine aussi la stabilité des ressources et la "
        "capacité du ménage à absorber un imprévu.",
        "Apport et épargne résiduelle\nL'apport peut financer une partie du prix et des "
        "frais d'acquisition. Conserver une épargne après l'achat limite le risque qu'une "
        "réparation ou une baisse temporaire de revenus déséquilibre immédiatement le "
        "budget. La composition exacte du dossier et la décision de crédit relèvent des "
        "règles de risque de la banque.",
        "Simulation et décision\nUne simulation traduit des hypothèses de montant, de "
        "durée et de taux en mensualité indicative. Elle ne constitue pas une offre ni "
        "une acceptation. La décision intervient après contrôle des justificatifs, du "
        "projet et de la garantie envisagée.",
        "Exemple fictif\nUn ménage compare deux durées de prêt et conserve une réserve "
        "pour les dépenses du logement. Les montants et le niveau d'effort de cet "
        "exemple seraient fictifs et ne formeraient aucun seuil universel.",
    ),
    "benchmark-mortgage-early-repayment": (
        "Préparer la demande\nL'emprunteur demande au prêteur un décompte pour une date "
        "déterminée et précise si le remboursement sera total ou partiel. Le document "
        "permet de distinguer capital restant dû, intérêts courus et frais éventuels "
        "avant de prendre une décision.",
        "Effets sur le prêt\nUn remboursement total clôt le financement après paiement "
        "des sommes dues. Un remboursement partiel peut réduire la durée ou les "
        "mensualités selon les options acceptées. Le montant minimal, les modalités de "
        "calcul et une éventuelle indemnité sont des règles contractuelles à vérifier "
        "dans l'offre et le décompte, dans les limites applicables.",
        "Comparer coût et bénéfice\nL'économie d'intérêts futurs doit être rapprochée "
        "des frais éventuels et de la perte de liquidité. Certaines situations prévues "
        "au contrat peuvent réduire les indemnités, mais aucune dispense générale n'est "
        "supposée ici. Une demande écrite conserve une trace de la date envisagée.",
        "Exemple fictif\nUn emprunteur compare une réduction de durée avec une baisse de "
        "mensualité à partir d'un décompte indicatif. Aucun montant ni résultat de cet "
        "exemple ne constitue une condition réelle de banque.",
    ),
    "benchmark-mortgage-fixed-variable": (
        "Taux fixe\nPendant la période convenue, la règle de calcul du taux fixe ne "
        "change pas. Cette stabilité facilite la prévision des mensualités et du coût, "
        "sans supprimer les autres éléments variables du projet, comme l'assurance ou "
        "certaines dépenses liées au logement.",
        "Taux révisable\nLe contrat relie le taux à un indice, une marge et une fréquence "
        "de révision. Une variation de l'indice peut modifier la mensualité ou la durée "
        "selon le mécanisme retenu. Un plafond peut limiter cette évolution uniquement "
        "s'il figure dans l'offre : il s'agit d'une protection contractuelle, non d'une "
        "caractéristique automatique.",
        "Choisir selon le risque\nLe client examine sa tolérance à une hausse d'échéance, "
        "son horizon de détention et la marge disponible dans son budget. Les exemples "
        "chiffrés de l'offre servent à comprendre le mécanisme ; ils ne prédisent pas "
        "l'évolution future de l'indice.",
        "Exemple fictif\nUn ménage simule une hausse et une baisse de l'indice avant de "
        "comparer un taux révisable à un taux fixe. Les valeurs utilisées sont des "
        "hypothèses pédagogiques, pas des prévisions de marché.",
    ),
    "benchmark-mortgage-guarantees": (
        "Fonction de la garantie\nLa garantie protège le prêteur si le crédit n'est plus "
        "remboursé. Selon le montage, elle peut porter sur le bien immobilier ou faire "
        "intervenir un organisme de caution. Elle ne dispense pas l'emprunteur de sa "
        "dette et ne remplace pas l'analyse de sa capacité de remboursement.",
        "Coûts et fin de financement\nLes frais de mise en place, les conditions de "
        "mainlevée ou de restitution éventuelle dépendent du mécanisme et des documents "
        "contractuels. Le client vérifie ces conséquences lors d'une vente, d'un "
        "remboursement anticipé ou d'un transfert de financement. Aucune restitution "
        "n'est présumée sans clause correspondante.",
        "Garantie et assurance\nUne garantie immobilière couvre le risque du prêteur sur "
        "le financement. L'assurance emprunteur peut couvrir certaines conséquences "
        "d'un décès, d'une incapacité ou d'une invalidité selon son contrat. L'assurance "
        "habitation protège le logement et certains biens selon une autre police. Ces "
        "protections ont donc des objets distincts.",
        "Exemple fictif\nUn acquéreur compare une sûreté sur le bien et une caution en "
        "examinant les frais initiaux et les conséquences d'une revente. Cet exemple "
        "n'indique aucune solution systématiquement préférable.",
    ),
    "benchmark-mortgage-offer": (
        "Lire le coût du financement\nL'offre rassemble le capital emprunté, la durée, "
        "les échéances, le taux et les coûts nécessaires au financement. Le taux annuel "
        "effectif global sert à regrouper les éléments de coût inclus selon les règles "
        "applicables ; le client vérifie les hypothèses et services retenus dans l'offre "
        "plutôt que de comparer le seul taux nominal.",
        "Clauses à examiner\nLes conditions de remboursement anticipé, de modulation, de "
        "retard, de garantie et d'assurance influencent la souplesse et le risque du "
        "contrat. Les modalités exactes sont contractuelles. Une simulation antérieure "
        "ne remplace pas le calendrier, les conditions particulières et les annexes de "
        "l'offre définitive.",
        "Contrôler la cohérence\nLe client rapproche l'identité des emprunteurs, le bien, "
        "le montant, l'apport et l'échéancier de son projet. Il demande une correction "
        "écrite en cas d'écart et conserve la version acceptée. La capacité future à "
        "supporter les mensualités reste distincte de la conformité formelle du document.",
        "Exemple fictif\nDeux offres affichent le même taux nominal mais des coûts "
        "annexes et des options différents. Leur comparaison pédagogique ne constitue "
        "ni une offre réelle ni une recommandation personnalisée.",
    ),
    "benchmark-insurance-borrower": (
        "Rôle de la couverture\nL'assurance emprunteur protège le remboursement du "
        "prêt lorsque l'événement déclaré correspond à une garantie du contrat. Selon "
        "la couverture choisie, l'assureur verse une part des échéances ou du capital "
        "restant dû. La banque reste créancière du prêt : une déclaration de sinistre "
        "ne suspend donc pas automatiquement les prélèvements.",
        "Quotité et examen du contrat\nLa quotité répartit la couverture entre les "
        "coemprunteurs. Elle doit être lue avec les définitions contractuelles de "
        "l'incapacité et de l'invalidité, les exclusions, la franchise et le délai de "
        "carence. Ce sont des règles contractuelles, variables selon l'offre, et non "
        "des paramètres universels. L'assuré vérifie aussi les justificatifs médicaux "
        "ou administratifs attendus et la procédure de déclaration.",
        "Articulation avec l'assurance habitation\nL'assurance emprunteur couvre le "
        "risque de non-remboursement lié à la personne assurée. L'assurance habitation "
        "couvre, selon son propre contrat, le logement, certains biens et la "
        "responsabilité civile. Protéger à la fois le logement et le crédit nécessite "
        "donc généralement deux couvertures distinctes ; aucune ne remplace l'autre.",
        "Exemple fictif\nDeux coemprunteurs choisissent des quotités différentes après "
        "avoir comparé leurs revenus et leur capacité à assumer seuls les échéances. "
        "Cet exemple illustre un raisonnement et ne prescrit aucune répartition.",
    ),
    "benchmark-insurance-payment-protection": (
        "Objet de l'assurance facultative\nCette assurance est associée à un crédit à "
        "la consommation. Elle peut prendre en charge certaines échéances si un "
        "événement garanti survient, sans effacer automatiquement la dette. Son "
        "caractère facultatif, son prix et ses garanties doivent être distingués des "
        "conditions du prêt lui-même.",
        "Conditions de prise en charge\nLe contrat définit précisément les événements "
        "couverts, les personnes admissibles, la durée maximale de prestation, les "
        "exclusions, la franchise et le délai de carence. Une perte d'emploi, une "
        "incapacité ou une situation médicale ne déclenche une prestation que si elle "
        "répond à ces définitions. Ces paramètres sont contractuels et doivent être "
        "vérifiés dans la notice de l'offre concernée.",
        "Démarche en cas d'événement\nL'emprunteur prévient l'assureur selon le canal "
        "prévu et transmet les justificatifs demandés. Pendant l'étude, il vérifie avec "
        "le prêteur si les échéances continuent d'être prélevées. Il conserve les "
        "références des échanges et signale rapidement tout changement de situation.",
        "Exemple fictif\nUne personne compare le coût total du crédit avec et sans "
        "assurance, puis confronte les exclusions à sa situation professionnelle. Les "
        "montants et choix d'un cas réel dépendraient de l'offre et du contrat.",
    ),
    "benchmark-consumer-difficulty": (
        "Signaler la difficulté tôt\nDès qu'une baisse de revenus ou une dépense "
        "imprévue menace une échéance, l'emprunteur établit un budget actualisé et "
        "contacte le prêteur avant l'accumulation d'impayés. Il indique les crédits "
        "concernés, la durée probable de la difficulté et la mensualité qu'il pense "
        "pouvoir assumer, sans masquer ses autres charges essentielles.",
        "Solutions à examiner\nLe prêteur peut étudier un changement de date, un report, "
        "un rééchelonnement ou une autre solution adaptée au dossier. Il ne s'agit pas "
        "de droits automatiques : toute modification dépend de l'accord du prêteur et "
        "doit préciser par écrit son effet sur la durée, le coût total et les prochaines "
        "échéances. Un allègement immédiat peut augmenter le coût futur.",
        "Limites et priorités\nContracter un nouveau crédit pour payer les échéances "
        "existantes peut déplacer la difficulté au lieu de la résoudre. L'emprunteur "
        "vérifie les conséquences d'un incident prévues par son contrat et sollicite, "
        "si nécessaire, un service d'accompagnement budgétaire compétent. Il conserve "
        "les propositions reçues et ne considère un accord comme acquis qu'après "
        "confirmation écrite.",
        "Exemple fictif\nAprès une réduction temporaire d'activité, une personne prépare "
        "trois mois de budget et demande une solution limitée dans le temps. Cet exemple "
        "n'implique aucune acceptation obligatoire par la banque.",
    ),
    "benchmark-payments-account-fees": (
        "Lire le relevé et la tarification\nLe relevé permet de rapprocher chaque frais "
        "de l'opération ou du service correspondant. La brochure tarifaire décrit les "
        "prix standards, tandis que la convention de compte précise les services "
        "souscrits et les conditions applicables au client. Une offre groupée doit être "
        "comparée aux services réellement utilisés.",
        "Découvert et incidents\nL'autorisation de découvert est une règle contractuelle "
        "qui fixe notamment une limite, une durée et un taux. Le relevé et les documents "
        "contractuels permettent d'identifier les intérêts et frais associés. Dépasser "
        "la limite convenue peut produire des coûts distincts et conduire au rejet de "
        "certaines opérations ; aucun seuil ni tarif universel n'est supposé ici.",
        "Contrôle et contestation\nLe client vérifie le libellé, la date, le montant et "
        "la période facturée. S'il ne comprend pas un débit, il consulte d'abord la "
        "tarification et sa convention, puis demande à la banque la base de calcul. Une "
        "alerte de solde aide au suivi quotidien mais ne remplace pas le contrôle du "
        "relevé.",
        "Exemple fictif\nUn client repère deux frais proches, constate qu'ils concernent "
        "des services différents et demande une explication documentée. Aucun montant "
        "de cet exemple ne constitue un tarif réel.",
    ),
    "benchmark-compliance-account-review": (
        "Finalité de la mise à jour\nLa revue du dossier permet à la banque de vérifier "
        "que les informations connues restent cohérentes avec la relation de compte. "
        "Elle peut porter sur l'identité, l'adresse, l'activité professionnelle, la "
        "résidence fiscale ou l'usage prévu des services. Une demande de mise à jour ne "
        "signifie pas, à elle seule, qu'une opération est suspecte.",
        "Vérifier puis répondre\nLe client confirme l'authenticité de la demande dans "
        "son espace bancaire ou auprès d'un contact officiel. Il transmet uniquement "
        "les pièces demandées par le canal sécurisé indiqué et demande une précision si "
        "le motif ou la liste des documents n'est pas clair. Les exigences exactes et "
        "la fréquence de revue relèvent du processus de la banque et du dossier, pas "
        "d'une périodicité universelle décrite ici.",
        "Dossier incomplet ou changement de situation\nUne pièce expirée, une adresse "
        "ancienne ou des réponses incohérentes peuvent entraîner une demande "
        "complémentaire. L'absence de réponse peut limiter certains services après les "
        "relances prévues. Le client conserve la preuve de transmission et actualise "
        "les informations lorsqu'un changement pertinent intervient.",
        "Exemple fictif\nAprès un changement d'emploi et d'adresse, une cliente vérifie "
        "la notification dans son application puis fournit les justificatifs demandés. "
        "Cet exemple décrit une pratique indicative, non une liste obligatoire.",
    ),
}

CURRENT_EDIT_IDS = {
    "benchmark-mortgage-capacity",
    "benchmark-mortgage-early-repayment",
    "benchmark-mortgage-fixed-variable",
    "benchmark-mortgage-guarantees",
    "benchmark-mortgage-offer",
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
    if document_id in PILOT_SECTIONS:
        return "\n\n".join(
            (
                f"Informations essentielles conservées\n{original_content}",
                *PILOT_SECTIONS[document_id],
            )
        )
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
    if len(documents) != 30 or len(reference_questions) != 40:
        raise ValueError("unexpected source dataset size")
    pilot_ids = set(PILOT_SECTIONS)
    for document in documents:
        word_count = len(document["content"].split())
        minimum, maximum = (200, 500) if document["id"] in pilot_ids else (300, 600)
        if not minimum <= word_count <= maximum:
            raise ValueError(
                f"unexpected word count for {document['id']}: {word_count}"
            )
    payload = {
        "schema_version": 2,
        "source_dataset": "rag_benchmark.json",
        "annotation_status": "unannotated",
        "documents": documents,
        "reference_questions": reference_questions,
    }
    if OUTPUT_PATH.exists():
        current = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        current_by_id = {document["id"]: document for document in current["documents"]}
        for document in documents:
            if (
                document["id"] not in CURRENT_EDIT_IDS
                and current_by_id.get(document["id"]) != document
            ):
                raise ValueError(f"non-pilot document changed: {document['id']}")
    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")
    print(f"Corpus v2 saved: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
