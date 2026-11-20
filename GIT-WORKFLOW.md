## Guidelines pour l'utilisation de git dans le projet

Lorsque que vous vous assignez un ticket, il est recommandé de créer la branche directement depuis GitHub, puis de checkout sur cette nouvelle branche.

```bash
git fetch origin
git checkout <branch_name>
```

Une fois le dev terminé, vous pouvez push vos modifications sur GitHub et ouvrir une PR.

Si des nouveaux commits ont été push sur main depuis la création de votre branche, vous pouvez mettre à jour votre branche main locale puis de rebase votre branche sur main:

```bash
git checkout main
git pull
git checkout <branch_name>
git rebase main
```
Lors du rebase il est possible que vous ayez des conflits, dans ce cas git vous dira quels fichiers sont concernés.
Une fois les conflits résolus à la main, vous devez les ajouter dans les staging changes et continuer le rebase:

```bash
git add .
git rebase --continue
```
git vous demandera alors le message du commit, vous pouvez le laisser tel quel si il vous convient.

Une fois le rebase terminé, le force push est obligatoire car votre branche locale diverge avec la branche distante.
Vérifiez bien que vous êtes sur la bonne branche et que tout votre travail est bien récupéré en local, puis vous pouvez lancer la commande:

```bash
git push --force
```

:warning: Attention si vous travaillez à plusieurs sur la même branche (ce qui est déconseillé), assurez-vous de ne pas écraser le travail des autres.
