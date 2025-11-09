# Contributing to DIRISI 2025 Backend

Merci de votre intérêt pour contribuer au projet ! 🎉

## 🚀 Quick Start

1. **Fork** le repo
2. **Clone** votre fork
3. **Créer** une branche pour votre feature
4. **Développer** et tester
5. **Soumettre** une Pull Request

## 📋 Checklist avant PR

- [ ] Le code est formaté avec `black` (`make fmt`)
- [ ] Le linting passe (`make lint`)
- [ ] Les tests passent (`make test`)
- [ ] Les nouveaux tests sont ajoutés si nécessaire
- [ ] La documentation est mise à jour
- [ ] Les changements sont décrits dans la PR

## 🏗️ Setup Développement

```bash
# Cloner
git clone https://github.com/YOUR_USERNAME/dirisi25-hackathon-backend.git
cd dirisi25-hackathon-backend

# Installer
make setup

# Lancer les tests
make test
```

## 📝 Standards de Code

### Python

- **Style** : PEP 8 (via `black` et `ruff`)
- **Docstrings** : Google style
- **Type hints** : Obligatoires pour les fonctions publiques
- **Line length** : 100 caractères

### Git

**Format des commits** :

```
type(scope): description courte

Description détaillée si nécessaire.

Fixes #123
```

**Types** :
- `feat`: Nouvelle fonctionnalité
- `fix`: Correction de bug
- `docs`: Documentation
- `test`: Tests
- `refactor`: Refactoring
- `chore`: Maintenance

**Exemples** :
```
feat(api): add /v1/optimize endpoint
fix(modeling): correct risk score calculation
docs(readme): update quickstart guide
```

## 🧪 Tests

- Ajouter des tests pour chaque nouvelle fonctionnalité
- Viser au moins 80% de couverture pour le code critique
- Utiliser `pytest` pour les tests

```bash
# Lancer tous les tests
make test

# Lancer un test spécifique
pytest tests/test_predict.py -v

# Avec coverage
pytest --cov=src --cov-report=html
```

## 📚 Documentation

- Mettre à jour le README si nécessaire
- Ajouter des docstrings pour les nouvelles fonctions/classes
- Commenter le code complexe

## 🔍 Review Process

1. **Automatique** : CI checks (lint, tests)
2. **Manuelle** : Review par un maintainer
3. **Merge** : Squash and merge

## ❓ Questions ?

Ouvrir une **Issue** avec le label `question`.

## 🙏 Merci !

Votre contribution est précieuse ! 💪
