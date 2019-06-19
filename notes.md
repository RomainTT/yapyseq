# Notes

## Wrappers multiples

Si je souhaite appeler un wrapper plusieurs fois, avec des paramètres différents pour chacun, comment faire ?
Par exemple un wrapper écrit pour établir une connexion avec **un** serveur. Si avant de lancer mon nœud je 
souhaite établir la connexion avec plusieurs, il faudrait que j’appelle le wrapper plusieurs fois.
(l’intérêt d’un wrapper dans ce cas est qu’il ferme tout seul la connexion à la fin du test).

