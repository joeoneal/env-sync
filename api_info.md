POST /auth/register (Email, Password)

POST /auth/login (Returns JWT)

POST /teams (Create a new team)

POST /teams/:id/invite (Send email to user)

GET /secrets/:team_id (Download encrypted blob)

POST /secrets/:team_id (Upload encrypted blob)