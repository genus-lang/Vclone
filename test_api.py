import main

data = main.ChapterRequest(
    text="""
[narrator] यह एक शांत रात थी। The night was silent.
[hero] Who is there?
[narrator] The door slowly opened...
[villain] You finally arrived.
[hero] I won't let you hurt them.
    """,
    language="en"
)

print("Sending chapter for generation directly...")
response = main.generate_chapter(data)
print("Success:", response)

