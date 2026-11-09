import streamlit as st

# Simple click check
if st.button("Say hello"):
  st.write("Why hello there")
else:
  st.write("Goodbye")

# Button with a primary style and an icon
if st.button("Click me", type="primary", icon="😃"):
  st.write("Button was clicked!")
