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
    "benchmark-consumer-personal-loan": (
        "Usage des fonds\nLe prêt personnel non affecté finance un besoin sans lier "
        "contractuellement le crédit à un achat précis. L'emprunteur n'a généralement "
        "pas à produire de facture d'utilisation, mais le prêteur analyse ses revenus, "
        "ses charges et ses crédits existants avant toute décision.",
        "Lecture de l'offre\nLe montant versé, la durée, les échéances, le taux, le coût "
        "total et les frais éventuels figurent dans les documents contractuels. Le "
        "client distingue la simulation indicative de l'offre définitive et vérifie les "
        "conditions de remboursement anticipé ou d'incident. L'acceptation reste soumise "
        "à l'étude du dossier.",
        "Souplesse et limite\nL'absence d'affectation donne de la liberté, mais elle "
        "signifie aussi que l'annulation du projet financé ne met pas automatiquement "
        "fin au crédit. L'emprunteur rapproche donc la durée du prêt de l'utilité du "
        "projet et conserve une marge pour ses charges essentielles.",
        "Exemple fictif\nUne personne compare deux durées pour financer plusieurs "
        "dépenses liées à un déménagement. Les montants et mensualités de cet exemple "
        "seraient pédagogiques et ne constitueraient aucune offre réelle.",
    ),
    "benchmark-consumer-assigned-loan": (
        "Lien entre achat et crédit\nLe crédit affecté finance un bien ou un service "
        "identifié dans le contrat. Le dossier doit donc permettre de rapprocher le "
        "vendeur, l'achat et le financement. Contrairement au prêt personnel, les fonds "
        "ne sont pas destinés à un usage libre.",
        "Sort de l'opération\nL'achat et le crédit sont juridiquement liés selon les "
        "conditions applicables au contrat : si le financement est refusé, l'achat "
        "financé ne se poursuit pas dans les conditions prévues. Le client vérifie que "
        "le bon de commande mentionne correctement le recours au crédit et ne présente "
        "pas le financement comme déjà accepté.",
        "Déblocage et remboursement\nLe versement intervient selon le processus prévu, "
        "souvent après confirmation de la livraison ou de la prestation. Montant, durée, "
        "échéancier, remboursement anticipé et conséquences d'un incident relèvent de "
        "l'offre contractuelle. Une difficulté avec le vendeur doit être documentée et "
        "signalée sans supposer que les prélèvements s'arrêtent automatiquement.",
        "Exemple fictif\nUn acheteur commande un équipement sous condition d'obtention "
        "du crédit indiqué au bon de commande. Cet exemple illustre le lien entre les "
        "contrats sans fixer de délai ni de procédure universelle.",
    ),
    "benchmark-consumer-revolving": (
        "Réserve réutilisable\nLe crédit renouvelable met à disposition une réserve dont "
        "la partie utilisée se reconstitue au fil des remboursements. Les intérêts sont "
        "calculés sur les sommes effectivement utilisées, pas sur la fraction disponible "
        "restée inutilisée.",
        "Coût et durée\nChaque utilisation modifie le capital à rembourser et peut "
        "allonger la durée si les mensualités restent faibles. Le contrat précise le "
        "taux, les échéances, les frais éventuels et les modalités de reconduction ou de "
        "résiliation. Le client suit le coût cumulé et distingue réserve disponible et "
        "argent déjà acquis.",
        "Utilisation prudente\nLa souplesse du produit convient à un besoin ponctuel mais "
        "peut masquer un endettement durable lorsque les utilisations se répètent. Une "
        "pratique indicative consiste à vérifier avant chaque tirage le solde dû, la "
        "durée estimée et la place de la nouvelle échéance dans le budget.",
        "Exemple fictif\nUne personne utilise une partie de sa réserve pour une réparation, "
        "puis cesse tout nouveau tirage jusqu'au remboursement. Les chiffres d'un tel "
        "scénario seraient fictifs et non une recommandation de financement.",
    ),
    "benchmark-consumer-early-repayment": (
        "Demander le montant à régler\nL'emprunteur indique au prêteur la date souhaitée "
        "et demande un décompte pour un remboursement total ou partiel. Le document "
        "distingue capital restant, intérêts courus et éventuels frais prévus afin "
        "d'éviter de confondre solde affiché et somme nécessaire à la clôture.",
        "Intérêts et effets\nLe remboursement anticipé supprime les intérêts futurs qui "
        "auraient porté sur le capital remboursé. Il ne supprime pas les intérêts déjà "
        "courus ni les sommes dues à la date de paiement. Un remboursement partiel peut "
        "modifier la durée ou les échéances selon les options contractuelles acceptées.",
        "Conditions à contrôler\nLe contrat et le décompte précisent le montant minimal, "
        "la procédure et une éventuelle indemnité dans les limites applicables. Le client "
        "compare l'économie attendue, les coûts et la liquidité qu'il conservera. Aucune "
        "exonération générale n'est supposée dans ce document.",
        "Exemple fictif\nUn emprunteur compare la clôture du prêt avec un remboursement "
        "partiel réduisant sa durée. Les montants et résultats sont des hypothèses "
        "pédagogiques, non des conditions bancaires réelles.",
    ),
    "benchmark-insurance-home-cover": (
        "Garanties à identifier\nL'assurance habitation peut couvrir l'incendie, le "
        "dégât des eaux, le vol et certains événements naturels selon la formule. Le "
        "client vérifie les locaux, les biens, les plafonds et les circonstances garantis "
        "plutôt que de déduire la couverture du seul nom de la garantie.",
        "Responsabilité et prévention\nLa responsabilité civile peut indemniser certains "
        "dommages causés involontairement à des tiers. Les activités professionnelles ou "
        "situations particulières ne sont pas automatiquement incluses. Les mesures de "
        "prévention réduisent le risque mais ne remplacent ni la garantie ni les "
        "obligations prévues au contrat.",
        "Indemnisation et limites\nFranchises, plafonds, exclusions, vétusté éventuelle "
        "et justificatifs déterminent l'indemnisation réelle. Ces éléments sont "
        "contractuels. L'assurance habitation protège le logement et certains biens ; "
        "elle ne remplace pas l'assurance emprunteur, qui couvre le remboursement du "
        "crédit selon des garanties liées à la personne.",
        "Exemple fictif\nUn locataire compare deux formules en examinant la couverture "
        "du vol, la franchise et le plafond des biens. Les valeurs de comparaison "
        "seraient fictives et ne décriraient aucun contrat commercial réel.",
    ),
    "benchmark-insurance-home-claim": (
        "Premières mesures\nAprès un sinistre, l'assuré protège les personnes et prend "
        "les mesures raisonnables pour éviter l'aggravation sans se mettre en danger. "
        "Il photographie les dommages, conserve si possible les biens atteints et garde "
        "les justificatifs des dépenses urgentes de sauvegarde.",
        "Déclaration et délai\nLa déclaration décrit la date, les circonstances, les "
        "dommages et les coordonnées utiles. Elle doit être transmise dans le délai "
        "prévu par le contrat d'assurance concerné. Ce corpus ne fixe volontairement "
        "aucune durée légale universelle : l'assuré consulte ses conditions contractuelles "
        "et contacte rapidement l'assureur en cas de doute.",
        "Instruction du dossier\nPhotographies, factures, devis, inventaire et constat "
        "peuvent étayer la demande. L'assureur peut solliciter des pièces complémentaires "
        "ou une expertise avant de déterminer l'indemnité. Sauf urgence de sécurité, une "
        "réparation définitive importante est différée jusqu'aux instructions de "
        "l'assureur, conformément au contrat.",
        "Exemple fictif\nAprès une fuite, une assurée coupe l'arrivée d'eau, photographie "
        "les pièces et vérifie dans son contrat le canal et le délai de déclaration. "
        "Aucune durée ni indemnité de cet exemple ne représente une règle réelle.",
    ),
    "benchmark-insurance-home-exclusions": (
        "Exclusion, franchise et plafond\nUne exclusion désigne une situation ou un "
        "dommage que le contrat ne garantit pas. La franchise est la part de l'indemnité "
        "qui reste à la charge de l'assuré. Le plafond limite le montant maximal pris en "
        "charge. Ces trois mécanismes ont des effets différents et sont définis dans les "
        "documents contractuels.",
        "Lire les conditions de garantie\nL'assuré rapproche l'événement déclaré, la "
        "cause, les biens concernés et les obligations de prévention des conditions "
        "générales et particulières. Une garantie mentionnée au contrat ne signifie pas "
        "que tout dommage associé sera indemnisé intégralement : franchise, plafond, "
        "vétusté éventuelle et exclusion peuvent réduire ou empêcher le versement.",
        "Cas particuliers\nUn défaut d'entretien, un usage professionnel du logement ou "
        "un bien de valeur peut relever de conditions spécifiques. La pratique utile "
        "consiste à demander une clarification écrite avant le sinistre lorsqu'une "
        "clause paraît ambiguë, et à ne pas présenter une exclusion propre à un contrat "
        "comme une règle commune à toutes les assurances.",
        "Exemple fictif\nPour un dommage évalué fictivement, une franchise contractuelle "
        "laisserait une part à payer même si le sinistre est couvert. Aucun montant de "
        "cet exemple ne correspond à une offre réelle.",
    ),
    "benchmark-savings-booklet": (
        "Disponibilité de l'épargne\nUn livret accueille des dépôts et permet généralement "
        "des retraits sans échéance fixe, sous réserve des modalités du produit. Cette "
        "liquidité le rend adapté à une réserve de précaution, qui doit rester accessible "
        "pour une dépense imprévue.",
        "Rémunération et opérations\nLes intérêts sont calculés selon les règles du "
        "livret. Taux, dates de valeur, minimum de versement, plafond éventuel et fréquence "
        "de capitalisation sont des dispositions propres au produit. Le client consulte "
        "la documentation contractuelle à jour plutôt que de supposer un taux ou un "
        "plafond universel.",
        "Usage et limites\nLa disponibilité ne garantit pas que le rendement compense "
        "l'évolution des prix. Une pratique indicative consiste à séparer la réserve de "
        "court terme des sommes destinées à un horizon plus long, puis à vérifier les "
        "délais pratiques de transfert vers le compte courant. Le livret n'est pas un "
        "compte-titres et n'expose pas directement à la fluctuation d'actions.",
        "Exemple fictif\nUne personne conserve plusieurs mois de dépenses imprévues sur "
        "un livret et automatise un versement modeste. Les montants et la rémunération "
        "de cet exemple seraient fictifs, sans valeur de conseil personnalisé.",
    ),
    "benchmark-savings-term-deposit": (
        "Principe du placement\nLe compte à terme reçoit une somme pour une durée "
        "convenue. Le contrat fixe l'échéance et la rémunération applicable en échange "
        "d'une disponibilité plus limitée que sur un livret. Le client rapproche donc "
        "la durée du dépôt de la date probable de son projet.",
        "Sortie avant l'échéance\nUne sortie anticipée peut être interdite, soumise à une "
        "pénalité ou entraîner une rémunération réduite selon le contrat. Délai de "
        "préavis, calcul des intérêts, renouvellement et restitution du capital sont "
        "également des dispositions contractuelles ; aucune modalité universelle n'est "
        "présumée dans ce corpus.",
        "Décision pratique\nAvant de bloquer les fonds, l'épargnant conserve séparément "
        "une réserve disponible et compare le rendement annoncé après coûts et conditions "
        "de sortie. Une rémunération connue ne supprime pas le risque de devoir récupérer "
        "l'argent plus tôt ni l'effet d'une évolution générale des prix.",
        "Exemple fictif\nUne personne place une somme dont elle n'anticipe pas l'usage "
        "avant une date donnée, tout en gardant son épargne d'urgence sur un livret. "
        "Durée, taux et pénalité seraient fictifs et non une offre réelle.",
    ),
    "benchmark-savings-securities-account": (
        "Fonction du compte-titres\nLe compte-titres permet de détenir et négocier des "
        "instruments financiers. Il constitue une enveloppe de conservation et "
        "d'opérations, pas une garantie de rendement. La valeur des titres peut monter "
        "ou baisser et une vente peut produire une perte en capital.",
        "Ordres, frais et information\nLe client vérifie le type d'ordre, la quantité, le "
        "prix ou la limite et la place de négociation avant validation. Frais de courtage, "
        "droits de garde éventuels, change et fiscalité applicable dépendent du service "
        "et de la situation. Les documents contractuels et tarifaires font foi ; aucune "
        "tarification universelle n'est supposée.",
        "Horizon et diversification\nUne pratique indicative consiste à relier chaque "
        "investissement à l'horizon, au besoin de liquidité et à la perte que l'épargnant "
        "peut supporter. Diversifier entre plusieurs émetteurs ou catégories réduit "
        "certains risques sans empêcher une baisse générale. Un titre complexe ou mal "
        "compris appelle une information supplémentaire avant l'ordre.",
        "Exemple fictif\nUne épargnante répartit une somme de long terme entre plusieurs "
        "titres après avoir isolé sa réserve disponible. Cette allocation est fictive et "
        "ne constitue ni une recommandation ni une promesse de performance.",
    ),
    "benchmark-savings-regular-plan": (
        "Automatiser les versements\nUn plan d'épargne programmé transfère à intervalles "
        "réguliers une somme définie vers un support choisi. L'automatisation installe "
        "une discipline d'épargne, mais elle ne garantit ni rendement ni disponibilité : "
        "ces caractéristiques dépendent du support destinataire.",
        "Paramètres à contrôler\nMontant, fréquence, date de prélèvement, durée et règles "
        "de modification sont précisés dans le mandat ou le contrat. Le client vérifie "
        "que le compte débité sera suffisamment approvisionné. Les frais, risques, "
        "conditions de sortie et éventuelle garantie du capital relèvent également des "
        "documents contractuels du support.",
        "Adapter l'effort d'épargne\nUne pratique indicative consiste à placer le "
        "versement après une entrée régulière de revenus, à conserver une réserve "
        "disponible et à réexaminer le montant lors d'un changement de budget. Suspendre "
        "ou réduire le programme peut éviter un découvert ; la procédure exacte dépend "
        "du service souscrit.",
        "Exemple fictif\nUne personne programme un versement mensuel vers un support de "
        "long terme et conserve séparément son épargne d'urgence. Le montant, la date "
        "et le rendement de cet exemple seraient fictifs et non une recommandation.",
    ),
    "benchmark-savings-risk-profile": (
        "Composantes du profil\nLe profil de risque rapproche l'objectif, l'horizon, les "
        "connaissances, l'expérience, le besoin de liquidité et la capacité financière "
        "à supporter une perte. La tolérance déclarée à la volatilité ne remplace pas "
        "l'analyse concrète des conséquences d'une baisse sur le projet du client.",
        "Horizon et capacité de perte\nUn horizon long peut laisser davantage de temps "
        "pour traverser des fluctuations, sans garantir la récupération du capital. Une "
        "somme nécessaire prochainement ne devrait pas être exposée au même risque qu'une "
        "épargne sans échéance proche. Cette mise en cohérence est une pratique indicative, "
        "pas une allocation universelle.",
        "Réévaluation et décision\nLe profil doit être actualisé lorsque les revenus, les "
        "charges, l'objectif ou l'échéance changent. Les caractéristiques, frais et "
        "risques de chaque produit restent définis par sa documentation contractuelle. "
        "La diversification réduit certains risques spécifiques sans supprimer une perte "
        "de marché générale.",
        "Exemple fictif\nDeux personnes ayant le même horizon choisissent différemment "
        "parce que l'une dépend de cette épargne pour un projet essentiel. Cet exemple "
        "illustre la capacité de perte et ne constitue aucun conseil d'investissement.",
    ),
    "benchmark-payments-card-opposition": (
        "Bloquer les opérations futures\nAprès la perte, le vol ou une compromission "
        "probable de la carte, le titulaire fait immédiatement opposition par le canal "
        "officiel de la banque. L'opposition vise à empêcher de nouvelles utilisations ; "
        "un simple verrouillage temporaire dans une application n'a pas nécessairement "
        "le même effet définitif.",
        "Informations à conserver\nLe client note la date, l'heure et la référence de "
        "l'opposition, puis suit les instructions concernant le remplacement de la carte. "
        "Il ne communique aucun code confidentiel à un appelant. Les modalités exactes, "
        "la responsabilité du titulaire et les démarches complémentaires relèvent du "
        "contrat et des règles applicables à la situation.",
        "Opposition et contestation\nL'opposition protège contre des opérations futures, "
        "mais ne traite pas automatiquement un paiement déjà comptabilisé. Le titulaire "
        "examine son relevé et conteste séparément les opérations inconnues avec leurs "
        "dates et montants. En cas de vol ou de fraude, il conserve les preuves utiles.",
        "Exemple fictif\nUne cliente ne retrouve plus sa carte, fait opposition depuis "
        "un canal vérifié puis signale un paiement antérieur inconnu. Cet exemple décrit "
        "deux démarches distinctes sans fixer de délai contractuel universel.",
    ),
    "benchmark-payments-card-dispute": (
        "Identifier l'opération\nAvant de contester, le titulaire vérifie le libellé, la "
        "date, le montant, les abonnements et les achats des cotitulaires. Si le paiement "
        "reste inconnu, il le signale rapidement à la banque par le canal prévu et "
        "transmet les informations permettant de l'identifier.",
        "Deux démarches complémentaires\nLa contestation demande l'examen d'une opération "
        "déjà passée. L'opposition à la carte cherche à empêcher de nouvelles opérations "
        "lorsque la carte ou ses données sont compromises. Constater un paiement inconnu "
        "et craindre d'autres débits peut donc justifier les deux actions, sans présumer "
        "de l'issue de la demande de remboursement.",
        "Instruction du dossier\nLa banque peut demander un formulaire, des échanges avec "
        "le commerçant ou d'autres justificatifs. Délais, motifs recevables et conditions "
        "de remboursement dépendent des règles applicables et du contrat. Le client "
        "conserve les références, surveille le compte et sécurise ses accès.",
        "Exemple fictif\nUn titulaire reconnaît un commerçant mais conteste un montant, "
        "tandis qu'un autre ne reconnaît pas du tout l'opération. Ces scénarios fictifs "
        "peuvent appeler des pièces différentes et ne garantissent aucun remboursement.",
    ),
    "benchmark-payments-transfer-fraud": (
        "Agir sans attendre\nAprès un virement frauduleux ou obtenu par tromperie, le "
        "client contacte immédiatement la banque par un canal officiel et demande une "
        "tentative de rappel des fonds. Cette tentative dépend de l'état du transfert et "
        "de la coopération des établissements ; elle ne garantit pas la récupération.",
        "Sécuriser et documenter\nLe client change les accès compromis, refuse toute "
        "nouvelle validation et rassemble l'IBAN, le montant, l'heure, les messages et "
        "les références d'appel. Il surveille les autres opérations et suit les "
        "instructions de signalement ou de plainte adaptées à sa situation.",
        "Comprendre la validation\nUne authentification forte confirme techniquement "
        "l'ordre validé, mais ne garantit pas l'honnêteté ni l'identité économique du "
        "bénéficiaire. La banque examine les circonstances selon le contrat et les règles "
        "applicables. Une promesse de récupération payante reçue ensuite doit être traitée "
        "comme un nouveau risque de fraude.",
        "Exemple fictif\nAprès avoir suivi un faux message, une personne valide un "
        "virement puis demande aussitôt son rappel et sécurise son accès. L'exemple ne "
        "préjuge ni du délai de traitement ni du remboursement final.",
    ),
    "benchmark-payments-standing-order": (
        "Deux modes de déclenchement\nLe virement permanent est programmé par le client, "
        "qui choisit le bénéficiaire, le montant, la fréquence et la date. Le prélèvement "
        "est présenté par un créancier sur la base d'une autorisation ; son montant peut "
        "varier, notamment pour une facture de consommation.",
        "Modifier ou révoquer\nLe client peut modifier ou supprimer un virement permanent "
        "selon les délais du service bancaire. La révocation d'un mandat de prélèvement "
        "empêche les présentations futures dans les conditions prévues, mais n'efface "
        "pas la dette envers le créancier. Une modification ne revient pas sur les "
        "opérations déjà exécutées.",
        "Contrôles utiles\nLes modalités de date d'effet, de rejet, de révocation et de "
        "contestation sont contractuelles. Une pratique indicative consiste à vérifier "
        "régulièrement les bénéficiaires, les mandats actifs, le solde avant l'échéance "
        "et les opérations comptabilisées. Un paiement déjà passé appelle une démarche "
        "distincte d'une simple suppression future.",
        "Exemple fictif\nUne personne arrête son virement mensuel vers un proche et "
        "révoque séparément le mandat d'un ancien fournisseur. Cet exemple illustre deux "
        "instructions différentes sans fixer de délai bancaire universel.",
    ),
    "benchmark-security-phishing": (
        "Signaux d'alerte\nUn message de phishing imite une banque pour provoquer un "
        "clic, la saisie d'un secret ou la validation d'une opération. L'urgence, la "
        "menace de blocage, une adresse inhabituelle et une demande de code sont des "
        "indices ; un logo correct ou le nom du client ne prouvent pas l'authenticité.",
        "Réaction sûre\nLe destinataire ne suit ni le lien ni le numéro fourni. Il ouvre "
        "lui-même l'application officielle ou utilise une coordonnée obtenue "
        "indépendamment. Il ne transmet jamais son mot de passe ou son code confidentiel "
        "complet et ne valide qu'une action qu'il a lui-même initiée et comprise.",
        "Après une interaction\nSi des identifiants ont été saisis ou une opération "
        "validée, le client contacte immédiatement la banque, sécurise ses accès et "
        "surveille le compte. Une validation de virement appelle aussi une demande rapide "
        "de rappel des fonds, sans garantie de récupération. Les procédures exactes "
        "relèvent du contrat et du canal de sécurité de la banque.",
        "Exemple fictif\nUn courriel annonce un blocage imminent ; la cliente ferme le "
        "message et vérifie son compte dans l'application ouverte séparément. Cet exemple "
        "est fictif et ne reproduit aucune communication bancaire réelle.",
    ),
    "benchmark-security-transfer-scam": (
        "Scénario du faux conseiller\nUn fraudeur peut afficher un numéro falsifié, citer "
        "des informations personnelles et présenter un virement comme une mesure de "
        "sécurité. Aucun compte prétendument sécurisé ne justifie de transférer son "
        "épargne sur instruction d'un appelant.",
        "Vérification indépendante\nLe client interrompt l'échange et rappelle la banque "
        "avec une coordonnée trouvée sur l'application, le site saisi manuellement ou un "
        "document connu. Pour une facture, toute modification soudaine d'IBAN est vérifiée "
        "auprès du fournisseur par un canal déjà établi. L'urgence ne remplace jamais "
        "ce contrôle.",
        "Réduire le risque et réagir\nPlafonds, alertes et double validation constituent "
        "des pratiques de réduction du risque, sans garantir l'honnêteté du bénéficiaire. "
        "Après un virement suspect, le client demande immédiatement un rappel, sécurise "
        "ses accès et conserve les preuves. Les suites et remboursements dépendent des "
        "circonstances et des règles applicables.",
        "Exemple fictif\nUn fournisseur semble annoncer un nouvel IBAN ; l'entreprise "
        "appelle son contact habituel avant tout paiement. Ce scénario fictif illustre "
        "une vérification et non une procédure contractuelle universelle.",
    ),
    "benchmark-security-strong-authentication": (
        "Principe de protection\nL'authentification forte combine au moins deux éléments "
        "indépendants, par exemple un secret, un appareil détenu ou une caractéristique "
        "biométrique. Elle renforce l'accès au compte et la validation de certaines "
        "opérations, mais ne prouve pas la légitimité économique d'une demande.",
        "Lire avant de valider\nLa notification doit être rapprochée de l'action initiée, "
        "du montant et du bénéficiaire affichés. En cas d'écart, le client refuse et "
        "contacte la banque par un canal officiel. Une validation forte confirme l'ordre "
        "technique ; elle ne garantit pas qu'un bénéficiaire est honnête ni qu'un appelant "
        "est réellement conseiller.",
        "Sécuriser l'appareil\nLe client garde ses codes secrets, verrouille et met à jour "
        "son téléphone, puis signale sa perte. La biométrie simplifie l'usage sans "
        "supprimer la nécessité de protéger l'appareil. Les méthodes disponibles et les "
        "vérifications supplémentaires sont définies par le service contractuel et son "
        "niveau de risque.",
        "Exemple fictif\nUne personne reçoit une demande de validation qu'elle n'a pas "
        "initiée, la refuse et ouvre elle-même l'application pour vérifier son compte. "
        "Cet exemple ne décrit aucune interface bancaire réelle.",
    ),
    "benchmark-compliance-funds-origin": (
        "Objet de la demande\nLa banque peut demander l'origine économique de fonds reçus "
        "ou destinés à une opération importante afin de comprendre la transaction et de "
        "remplir ses obligations. Cette demande ne signifie pas, à elle seule, que les "
        "fonds ou le client sont considérés comme illégaux.",
        "Justificatifs selon le contexte\nUne vente peut être étayée par un acte et un "
        "relevé ; une succession par une attestation correspondante ; une rémunération ou "
        "une opération commerciale par un contrat, un relevé ou un document fiscal "
        "pertinent. La liste exacte dépend du dossier et de la demande de la banque : "
        "aucune pièce unique ne convient à toutes les situations.",
        "Répondre de manière proportionnée\nLe client vérifie l'authenticité de la "
        "sollicitation, transmet uniquement les documents nécessaires par le canal "
        "sécurisé indiqué et explique les liens entre les pièces et le mouvement. La "
        "banque peut poser des questions complémentaires si les informations ne suffisent "
        "pas. Ces contrôles relèvent de son processus, pas d'un seuil fictif du corpus.",
        "Exemple fictif\nAprès la vente d'un bien, une cliente joint l'acte et la trace "
        "du versement demandés dans son espace sécurisé. Ce scénario fictif n'établit "
        "aucune liste obligatoire ni aucun montant déclencheur.",
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
    "benchmark-payments-standing-order",
    "benchmark-security-phishing",
    "benchmark-security-transfer-scam",
    "benchmark-security-strong-authentication",
    "benchmark-compliance-funds-origin",
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
