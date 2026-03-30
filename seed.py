"""Run once to populate demo data: python seed.py"""
from app import app, db
from models import User, Project, Bid

with app.app_context():
    db.create_all()

    if User.query.first():
        print("Database already seeded. Delete instance/collabhub.db to re-seed.")
        exit()

    admin = User(name="Admin", email="admin@collabhub.io", role="admin",
                 status="approved", bio="Platform administrator")
    admin.set_password("admin")

    alice = User(name="Alice Chen", email="alice@uni.edu", status="approved",
        bio="Machine learning researcher focused on NLP, transformer architectures, and few-shot learning. Interested in applying LLMs to scientific discovery.",
        website="https://alicechen.dev", linkedin="https://linkedin.com/in/alicechen",
        scholar="https://scholar.google.com/alicechen")
    alice.set_password("pass")

    bob = User(name="Bob Martinez", email="bob@uni.edu", status="approved",
        bio="Full-stack developer and data engineer with expertise in distributed systems, real-time pipelines, and cloud-native architectures.",
        website="https://bobmartinez.io", linkedin="https://linkedin.com/in/bobm")
    bob.set_password("pass")

    carol = User(name="Carol Wang", email="carol@uni.edu", status="approved",
        bio="UX researcher and designer specializing in human-AI interaction, accessibility, and participatory design. Background in cognitive science.",
        linkedin="https://linkedin.com/in/carolwang", scholar="https://scholar.google.com/carolwang")
    carol.set_password("pass")

    dan = User(name="Dan Okafor", email="dan@uni.edu", status="approved",
        bio="Computational biologist working on protein structure prediction, genomics, and bioinformatics. Experience with deep learning for drug discovery.",
        website="https://danokafor.com", linkedin="https://linkedin.com/in/danokafor",
        scholar="https://scholar.google.com/danokafor")
    dan.set_password("pass")

    elena = User(name="Elena Petrov", email="elena@uni.edu", status="approved",
        bio="Statistician and data scientist with expertise in causal inference, Bayesian methods, and experimental design. Interested in public policy.",
        linkedin="https://linkedin.com/in/elenap", scholar="https://scholar.google.com/elenap")
    elena.set_password("pass")

    frank = User(name="Frank Nguyen", email="frank@uni.edu", status="pending",
        bio="Computer vision researcher working on 3D reconstruction, autonomous driving perception, and multi-modal learning.",
        website="https://franknguyen.ai", linkedin="https://linkedin.com/in/frankn")
    frank.set_password("pass")

    db.session.add_all([admin, alice, bob, carol, dan, elena, frank])
    db.session.flush()

    p1 = Project(owner_id=alice.id, title="AI-Powered Literature Review Assistant",
        description="Building an intelligent tool that uses LLMs to help researchers navigate and synthesize scientific literature, identifying themes, contradictions, and gaps across papers.",
        mode="public", status="open")
    p2 = Project(owner_id=dan.id, title="Protein Interaction Network Visualizer",
        description="Creating an interactive web platform for visualizing protein-protein interaction networks using graph neural networks to predict novel interactions.",
        mode="public", status="open")
    db.session.add_all([p1, p2])
    db.session.flush()

    db.session.add_all([
        Bid(project_id=p1.id, user_id=bob.id, message="I can build the full-stack platform and data pipeline for ingesting papers."),
        Bid(project_id=p1.id, user_id=carol.id, message="I'd love to design the UX for the knowledge maps and ensure accessibility."),
        Bid(project_id=p1.id, user_id=elena.id, message="I can contribute statistical methods for identifying significant themes across papers."),
        Bid(project_id=p2.id, user_id=alice.id, message="I can contribute NLP components for extracting interaction evidence from abstracts."),
        Bid(project_id=p2.id, user_id=bob.id, message="Happy to build the web visualization platform and API layer."),
    ])
    db.session.commit()
    print("Database seeded successfully!")
    print()
    print("Demo accounts:")
    print("  Admin:   admin@collabhub.io / admin")
    print("  Users:   alice@uni.edu, bob@uni.edu, carol@uni.edu, dan@uni.edu, elena@uni.edu / pass")
    print("  Pending: frank@uni.edu / pass")