import smtplib

EMAIL_USER=""
EMAIL_PASSWORD=""

server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()

server.login(EMAIL_USER, EMAIL_PASSWORD)
print("LOGIN OK!")
