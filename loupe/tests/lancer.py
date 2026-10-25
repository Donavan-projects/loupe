#!/usr/bin/env python3
"""Jeu de test de Loupe : relance les analyses de exemples.json et affiche un tableau comparatif.

Usage, depuis la racine du dépôt :
  python3 loupe/tests/lancer.py                        # workflow « Loupe — Analyse » actif (URL de production)
  python3 loupe/tests/lancer.py --test                 # workflow inactif : cliquer sur « Execute workflow » avant chaque analyse
  python3 loupe/tests/lancer.py --seulement Decathlon  # une seule entreprise (option répétable)
  python3 loupe/tests/lancer.py --modele gpt-6.1-sol   # modèle de rédaction, pris dans loupe/config/modeles.json
  python3 loupe/tests/lancer.py --executions 12,15     # tableau à partir d'exécutions existantes, sans rien relancer

Après chaque analyse, les tokens et le coût estimé sont enregistrés dans loupe.analyses (--sans-enregistrement pour
ne rien écrire). La clé d'API est lue dans N8N_API_KEY ou dans le fichier .env du dépôt ; elle n'est jamais affichée.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
BASE = os.environ.get('LOUPE_N8N_URL', 'http://localhost:5678').rstrip('/')
# Identifiant du workflow « Loupe — Analyse » dans votre instance (visible dans son URL).
WORKFLOW_ID = os.environ.get('LOUPE_WORKFLOW_ID', '')
CHEMIN_FORMULAIRE = 'loupe-analyse'
CHAMPS = ['entreprise', 'url', 'contexte', 'modele']  # ordre des champs du formulaire : field-0 … field-3
DELAI_MAX_S = 300
EN_COURS = {'new', 'running'}
NOEUDS_DE_FIN = {'Page résultat', 'Page erreur'}
NOEUDS_MODELE = ['Modèle OpenAI', 'Modèle rédaction']
# Lecture de page en échec : message court de l'outil (depuis la v2.8) ou objet d'erreur de l'ancien outil.
ECHEC_LECTURE = re.compile(r'^\s*(Page inaccessible|Ce lien est un fichier|There was an error)|^\s*\[?\s*\{\s*\\*"error', re.I)
CONTENEUR_POSTGRES = os.environ.get('LOUPE_CONTENEUR_POSTGRES', 'loupe-postgres')
ENV_POSTGRES = RACINE / '.env'
CONFIG = json.loads((RACINE / 'loupe/config/modeles.json').read_text(encoding='utf-8'))
# Anglicismes courants dans des notes produit, quand un terme français existe (détection indicative).
ANGLICISMES = ['onboarding', 'churn', 'upsell', 'upselling', 'cross-sell', 'fulfilment', 'fulfillment', 'batching', 'data-driven',
               'dashboard', 'workflow', 'template', 'templates', 'checklist', 'feedback', 'reporting', 'packaging', 'marketplace',
               'mapping', 'pricing', 'roadmap', 'insight', 'insights', 'lead', 'leads', 'tracking', 'matching', 'scoring',
               'benchmark', 'business', 'customer', 'retention', 'best-effort', 'quick win', 'use case', 'self-service',
               'opt-in', 'pipeline', 'backlog', 'monitoring', 'process', 'kit', 'pack', 'playbook', 'webinar', 'newsletter']


def cle_api():
    cle = os.environ.get('N8N_API_KEY')
    if not cle:
        env = RACINE / '.env'
        if env.exists():
            for ligne in env.read_text(encoding='utf-8').splitlines():
                if ligne.strip().startswith('N8N_API_KEY='):
                    cle = ligne.split('=', 1)[1].strip().strip('"').strip("'")
    if not cle:
        sys.exit("Clé d'API introuvable : définir N8N_API_KEY ou renseigner le fichier .env du dépôt.")
    return cle


def api(chemin, cle):
    requete = urllib.request.Request(BASE + '/api/v1' + chemin, headers={'X-N8N-API-KEY': cle})
    with urllib.request.urlopen(requete, timeout=60) as reponse:
        return json.load(reponse)


def verifier_modele(modele):
    """Refuse, avant tout envoi, un modèle absent de la liste blanche ou au-delà du tarif d'entrée maximal."""
    tarif = CONFIG['modeles'].get(modele)
    if not tarif:
        sys.exit('Modèle non autorisé : %s (liste blanche : %s).' % (modele, ', '.join(CONFIG['modeles'])))
    if not tarif['entree'] <= CONFIG['prix_max_entree_par_million']:
        sys.exit("Modèle non autorisé : %s dépasse %s $ par million de tokens en entrée." % (modele, CONFIG['prix_max_entree_par_million']))


def derniere_execution(cle):
    """Plus grand identifiant d'exécution connu, tous workflows confondus."""
    donnees = api('/executions?limit=1', cle)['data']
    return int(donnees[0]['id']) if donnees else 0


def soumettre(entree, mode_test):
    """Envoie le formulaire comme le ferait le navigateur (multipart/form-data)."""
    limite = '----loupe' + uuid.uuid4().hex
    corps = b''
    for index, champ in enumerate(CHAMPS):
        valeur = str(entree.get(champ) or '')
        corps += ('--%s\r\nContent-Disposition: form-data; name="field-%d"\r\n\r\n%s\r\n' % (limite, index, valeur)).encode('utf-8')
    corps += ('--%s--\r\n' % limite).encode('utf-8')
    url = '%s/%s/%s' % (BASE, 'form-test' if mode_test else 'form', CHEMIN_FORMULAIRE)
    requete = urllib.request.Request(url, data=corps, method='POST',
                                     headers={'Content-Type': 'multipart/form-data; boundary=' + limite})
    with urllib.request.urlopen(requete, timeout=DELAI_MAX_S) as reponse:
        texte = reponse.read().decode('utf-8', 'replace')
    try:
        return json.loads(texte)
    except ValueError:
        return {}


def lire_execution(identifiant, cle):
    """Données d'une exécution, ou None si elle n'existe pas (encore)."""
    try:
        return api('/executions/%s?includeData=true' % identifiant, cle)
    except urllib.error.HTTPError as erreur:
        if erreur.code == 404:
            return None
        raise


def trouver_execution(apres, reponse, cle):
    """Identifiant de l'exécution lancée par le formulaire.

    La liste de l'API omet les exécutions de production en attente de la page de fin :
    l'identifiant est lu dans la réponse du formulaire, sinon cherché parmi les suivants de `apres`.
    """
    trouve = re.search(r'/form-waiting/(\d+)', str(reponse.get('formWaitingUrl') or ''))
    if trouve:
        return int(trouve.group(1))
    for identifiant in range(apres + 1, apres + 40):
        detail = lire_execution(identifiant, cle)
        if detail and detail.get('workflowId') == WORKFLOW_ID:
            return identifiant
    return None


def attendre(apres, reponse, cle):
    """Attend la fin de l'exécution lancée par le formulaire et renvoie ses données."""
    debut = time.time()
    identifiant = None
    while time.time() - debut < DELAI_MAX_S:
        time.sleep(3)
        identifiant = identifiant or trouver_execution(apres, reponse, cle)
        detail = lire_execution(identifiant, cle) if identifiant else None
        if not detail or detail.get('status') in EN_COURS:
            continue
        # Une exécution « waiting » attend seulement l'affichage de la page de fin : l'analyse est terminée.
        dernier = ((detail.get('data') or {}).get('resultData') or {}).get('lastNodeExecuted')
        if detail.get('status') != 'waiting' or dernier in NOEUDS_DE_FIN:
            return detail
    return None


def json_du_noeud(runs, nom):
    """Premier item de la sortie principale du dernier passage d'un nœud, ou None."""
    passages = runs.get(nom) or []
    for passage in reversed(passages):
        for sortie in ((passage.get('data') or {}).get('main') or []):
            if sortie:
                return sortie[0].get('json') or {}
    return None


def consommation(runs):
    """Tokens et coût des appels au modèle d'une exécution, d'après les données conservées par n8n.

    n8n conserve soit les tokens rapportés par OpenAI (`tokenUsage`), soit une estimation (`tokenUsageEstimate`)
    qui ignore les tokens de raisonnement et la sortie des appels d'outils : le coût est alors un minimum.
    """
    bilan = {'entree': 0, 'sortie': 0, 'cout': 0.0, 'appels': 0, 'appels_estimes': 0, 'modeles': set(), 'inconnus': set()}
    for noeud in NOEUDS_MODELE:
        for passage in runs.get(noeud) or []:
            try:
                donnees = passage['data']['ai_languageModel'][0][0]['json']
            except (KeyError, IndexError, TypeError):
                continue
            try:
                modele = passage['inputOverride']['ai_languageModel'][0][0]['json']['options']['model']
            except (KeyError, IndexError, TypeError):
                modele = None
            reel = donnees.get('tokenUsage') or {}
            usage = reel if reel.get('promptTokens') else (donnees.get('tokenUsageEstimate') or {})
            entree, sortie = int(usage.get('promptTokens') or 0), int(usage.get('completionTokens') or 0)
            bilan['appels'] += 1
            bilan['appels_estimes'] += 0 if reel.get('promptTokens') else 1
            bilan['entree'] += entree
            bilan['sortie'] += sortie
            tarif = CONFIG['modeles'].get(modele)
            if tarif:
                bilan['modeles'].add(modele)
                bilan['cout'] += (entree * tarif['entree'] + sortie * tarif['sortie']) / 1e6
            else:
                bilan['inconnus'].add(str(modele))
    return bilan


def anglicismes(*textes):
    """Anglicismes de la liste présents dans les textes (mots entiers, sans tenir compte de la casse)."""
    def chaines(valeur):
        if isinstance(valeur, str):
            yield valeur
        elif isinstance(valeur, dict):
            for cle, element in valeur.items():
                if cle not in ('source', 'citation', 'url', 'pages_analysees'):
                    yield from chaines(element)
        elif isinstance(valeur, list):
            for element in valeur:
                yield from chaines(element)
    texte = ' '.join(chaine for valeur in textes for chaine in chaines(valeur)).lower()
    return [mot for mot in ANGLICISMES if re.search(r'(?<![\w-])%s(?![\w-])' % re.escape(mot), texte)]


def resumer(detail):
    """Extrait d'une exécution les éléments à comparer."""
    resultat = (detail.get('data') or {}).get('resultData') or {}
    runs = resultat.get('runData') or {}
    formulaire = json_du_noeud(runs, 'Formulaire') or {}
    config = json_du_noeud(runs, 'Configuration modèles') or {}
    ligne = {'execution': detail.get('id'), 'entreprise': formulaire.get('entreprise') or '?',
             'contexte': bool(str(formulaire.get('contexte') or '').strip()),
             'analyse_id': (json_du_noeud(runs, 'Créer analyse') or {}).get('id'),
             'modele': config.get('modele_redaction') or 'gpt-5-mini',
             'statut': '?', 'pages': [], 'duree_s': None, 'heures': None, 'heures_brutes': None, 'tours': None,
             'avertissements': [], 'pistes_signalees': [], 'regenerees': 0, 'anglicismes': [], 'piste_retenue': None}

    # L'agent s'appelle « Agent exploration » depuis la v2.8, « Agent teardown » dans les exécutions antérieures.
    agent = json_du_noeud(runs, 'Agent exploration') or json_du_noeud(runs, 'Agent teardown') or {}
    for etape in agent.get('intermediateSteps') or []:
        observation = etape.get('observation')
        observation = observation if isinstance(observation, str) else json.dumps(observation or '')
        try:  # l'outil renvoie son texte dans une enveloppe JSON : [{"response": "…"}]
            enveloppe = json.loads(observation)
            premier = enveloppe[0] if isinstance(enveloppe, list) and enveloppe else enveloppe
            if isinstance(premier, dict) and isinstance(premier.get('response'), str):
                observation = premier['response']
        except ValueError:
            pass
        entree = (etape.get('action') or {}).get('toolInput') or {}
        url = (entree.get('url') or entree.get('query') or '?') if isinstance(entree, dict) else str(entree)
        echec = bool(ECHEC_LECTURE.search(observation))
        ligne['pages'].append(('✗ ' if echec else '') + (urllib.parse.urlparse(url).path or '/'))

    finale = json_du_noeud(runs, 'Analyse finale') or {}
    for piste in finale.get('pistes_signalees') or []:
        suite = ' → ' + piste['nouveau_titre'] if piste.get('nouveau_titre') else ''
        ligne['pistes_signalees'].append('%s (%s)%s' % (piste.get('titre'), piste.get('action'), suite))
        ligne['regenerees'] += 1 if piste.get('action') == 'régénérée' else 0

    premiere = json_du_noeud(runs, 'Calculer durée') or {}
    duree = json_du_noeud(runs, 'Recalculer durée') or premiere
    proof_of_work = duree.get('proof_of_work') or {}
    ligne['heures'] = proof_of_work.get('duree_calculee_heures')
    ligne['piste_retenue'] = proof_of_work.get('piste_retenue')
    ligne['heures_brutes'] = premiere.get('duree_totale')
    ligne['tours'] = (duree.get('tentatives_pow') or 1) - 1 if duree else None
    termes = [a.get('terme') for a in (duree.get('avertissements') or []) if isinstance(a, dict)]
    ligne['avertissements'] = list(dict.fromkeys(t for t in termes if t))
    ligne['anglicismes'] = anglicismes(finale.get('output') or agent.get('output') or {}, proof_of_work)

    bilan = consommation(runs)
    ligne.update({'tokens_entree': bilan['entree'], 'tokens_sortie': bilan['sortie'], 'cout': round(bilan['cout'], 4),
                  'cout_estime': bilan['appels_estimes'] > 0, 'appels': bilan['appels'], 'appels_estimes': bilan['appels_estimes'],
                  'modeles_inconnus': sorted(bilan['inconnus'])})
    if bilan['cout'] > CONFIG['seuil_avertissement_cout']:
        ligne['avertissements'].append('coût estimé de %.2f $ (plus de %.2f $)' % (bilan['cout'], CONFIG['seuil_avertissement_cout']))

    enregistre = json_du_noeud(runs, 'Enregistrer analyse')
    erreur = json_du_noeud(runs, 'Enregistrer erreur')
    if enregistre and enregistre.get('duree_ms') is not None:
        ligne['statut'] = 'terminé'
        ligne['duree_s'] = round(enregistre['duree_ms'] / 1000)
    elif erreur is not None:
        ligne['statut'] = 'erreur : ' + str(erreur.get('message_page') or '').replace('Analyse impossible : ', '')[:60]
    elif resultat.get('error'):
        ligne['statut'] = 'échec : ' + str(resultat['error'].get('message'))[:60]
    else:
        ligne['statut'] = str(detail.get('status'))
    return ligne


def enregistrer(ligne):
    """Écrit les tokens et le coût estimé dans loupe.analyses, et l'avertissement de coût s'il y a lieu."""
    if not ligne.get('analyse_id') or not ligne.get('appels'):
        return False
    utilisateur = base = None
    for texte in ENV_POSTGRES.read_text(encoding='utf-8').splitlines():
        if texte.startswith('POSTGRES_USER='):
            utilisateur = texte.split('=', 1)[1].strip().strip('"').strip("'")
        if texte.startswith('POSTGRES_DB='):
            base = texte.split('=', 1)[1].strip().strip('"').strip("'")
    seuil = CONFIG['seuil_avertissement_cout']
    avertissement = json.dumps([{'terme': 'coût estimé de %.2f $ (plus de %.2f $)' % (ligne['cout'], seuil), 'champ': 'cout_estime'}], ensure_ascii=False)
    requete = """
        UPDATE loupe.analyses
        SET tokens_entree = :entree, tokens_sortie = :sortie, cout_estime = :cout,
            avertissements = CASE WHEN :cout > :seuil AND NOT coalesce(avertissements, '[]'::jsonb) @> :'avertissement'::jsonb
                                  THEN coalesce(avertissements, '[]'::jsonb) || :'avertissement'::jsonb ELSE avertissements END
        WHERE id = :'id'::uuid;
    """
    commande = ['docker', 'exec', '-i', CONTENEUR_POSTGRES, 'psql', '-q', '-v', 'ON_ERROR_STOP=1', '-U', utilisateur or 'postgres', '-d', base or 'loupe',
                '-v', 'entree=%d' % ligne['tokens_entree'], '-v', 'sortie=%d' % ligne['tokens_sortie'], '-v', 'cout=%.4f' % ligne['cout'],
                '-v', 'seuil=%.4f' % seuil, '-v', 'avertissement=' + avertissement, '-v', 'id=' + str(ligne['analyse_id'])]
    try:
        subprocess.run(commande, input=requete, text=True, check=True, capture_output=True, timeout=30)
        return True
    except (subprocess.SubprocessError, OSError):
        return False


def heures(valeur):
    return ('%s h' % valeur).replace('.', ',') if valeur is not None else '—'


def afficher(lignes):
    colonnes = [('Entreprise', lambda l: l['entreprise'] + (' *' if l['contexte'] else '')),
                ('Exéc.', lambda l: l['execution']),
                ('Rédaction', lambda l: l['modele']),
                ('Statut', lambda l: l['statut']),
                ('Pages', lambda l: '%d lues, %d en échec' % (len([p for p in l['pages'] if not p.startswith('✗')]), len([p for p in l['pages'] if p.startswith('✗')]))),
                ('Entrée', lambda l: l['tokens_entree'] if l['appels'] else '—'),
                ('Coût', lambda l: ('≥ ' if l['cout_estime'] else '') + ('%.3f $' % l['cout']).replace('.', ',') if l['appels'] else '—'),
                ('Durée', lambda l: '%s s' % l['duree_s'] if l['duree_s'] is not None else '—'),
                ('PoW brut', lambda l: heures(l['heures_brutes'])),
                ('PoW final', lambda l: heures(l['heures'])),
                ('Tours', lambda l: l['tours'] if l['tours'] is not None else '—'),
                ('Pistes régén.', lambda l: l['regenerees']),
                ('Avert.', lambda l: len(l['avertissements'])),
                ('Anglic.', lambda l: len(l['anglicismes']))]
    tableau = [[titre for titre, _ in colonnes]] + [[str(valeur(l)) for _, valeur in colonnes] for l in lignes]
    largeurs = [max(len(rangee[i]) for rangee in tableau) for i in range(len(colonnes))]
    print()
    for numero, rangee in enumerate(tableau):
        print('  '.join(cellule.ljust(largeurs[i]) for i, cellule in enumerate(rangee)).rstrip())
        if numero == 0:
            print('  '.join('-' * largeur for largeur in largeurs))
    print('\n* analyse lancée avec un contexte')
    print('≥ coût minimal : au moins un appel sans tokens rapportés par OpenAI, estimé par n8n sans les tokens de raisonnement\n')
    for l in lignes:
        print('%s — %s (exécution %s)' % (l['entreprise'], l['modele'], l['execution']))
        print('  pages lues       : ' + (' · '.join(l['pages']) or '—'))
        if l['appels']:
            print('  tokens           : %d en entrée, %d en sortie, sur %d appels dont %d estimés' % (l['tokens_entree'], l['tokens_sortie'], l['appels'], l['appels_estimes']))
        if l['modeles_inconnus']:
            print('  modèles sans tarif : ' + ', '.join(l['modeles_inconnus']))
        print('  avertissements   : ' + (' · '.join(l['avertissements']) or 'aucun'))
        print('  pistes signalées : ' + (' · '.join(l['pistes_signalees']) or 'aucune'))
        print('  piste retenue    : ' + (l['piste_retenue'] or '—'))
        print('  anglicismes      : ' + (', '.join(l['anglicismes']) or 'aucun'))


def main():
    parseur = argparse.ArgumentParser(description='Relance les analyses de Loupe et compare les résultats.')
    parseur.add_argument('--fichier', default=str(Path(__file__).with_name('exemples.json')))
    parseur.add_argument('--seulement', action='append', default=[], help="nom d'entreprise à lancer (répétable)")
    parseur.add_argument('--modele', help='modèle de rédaction, pris dans loupe/config/modeles.json (défaut : celui du workflow)')
    parseur.add_argument('--test', action='store_true', help="URL de test du formulaire : cliquer sur « Execute workflow » avant chaque analyse")
    parseur.add_argument('--executions', help="identifiants d'exécutions existantes, séparés par des virgules (rien n'est relancé)")
    parseur.add_argument('--sans-enregistrement', action='store_true', help='ne pas écrire les tokens et le coût dans loupe.analyses')
    options = parseur.parse_args()
    cle = cle_api()
    if not WORKFLOW_ID:
        sys.exit('Définir LOUPE_WORKFLOW_ID : identifiant du workflow « Loupe — Analyse » dans votre instance.')
    if options.modele:
        verifier_modele(options.modele)

    if options.executions:
        lignes = [resumer(api('/executions/%s?includeData=true' % identifiant.strip(), cle)) for identifiant in options.executions.split(',')]
    else:
        entrees = json.loads(Path(options.fichier).read_text(encoding='utf-8'))
        if options.seulement:
            voulus = {nom.lower() for nom in options.seulement}
            entrees = [e for e in entrees if e.get('entreprise', '').lower() in voulus]
        entrees = [e for e in entrees if e.get('entreprise') and e.get('url')]
        if not entrees:
            sys.exit('Aucune entreprise à lancer.')
        if not options.test and not api('/workflows/' + WORKFLOW_ID, cle).get('active'):
            sys.exit("Le workflow « Loupe — Analyse » est inactif : l'activer, ou relancer avec --test.")

        lignes = []
        for numero, entree in enumerate(entrees, 1):
            entree = dict(entree, modele=options.modele or '')
            print('[%d/%d] %s…' % (numero, len(entrees), entree['entreprise']), flush=True)
            if options.test:
                input('      Clique sur « Execute workflow » dans n8n, puis appuie sur Entrée. ')
            avant = derniere_execution(cle)
            try:
                reponse = soumettre(entree, options.test)
            except urllib.error.HTTPError as erreur:
                print('      formulaire refusé (HTTP %s)' % erreur.code)
                continue
            detail = attendre(avant, reponse, cle)
            if detail is None:
                print('      aucune exécution terminée après %d s' % DELAI_MAX_S)
                continue
            ligne = resumer(detail)
            lignes.append(ligne)
            print('      %s' % ligne['statut'])

    if not options.sans_enregistrement:
        ecrites = sum(1 for ligne in lignes if enregistrer(ligne))
        print('\nTokens et coût enregistrés pour %d analyse(s) sur %d.' % (ecrites, len(lignes)))
    afficher(lignes)


if __name__ == '__main__':
    main()
