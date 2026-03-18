const fs = require('fs');

const syllabusData = {
  "streams": {
    "MBBS": {
      "Anatomy": [
        { "chapter": "General Anatomy", "topics": ["Introduction to Anatomical Terms", "Epithelium and Connective Tissue Overview", "Cartilage and Bone Structure", "Joints Classification", "Muscular System Basics", "Cardiovascular System Overview", "Lymphatic System", "Nervous System Intro"] },
        { "chapter": "Upper Limb", "topics": ["Pectoral Region Elements", "Axilla and Brachial Plexus", "Arm and Cubital Fossa", "Forearm Anatomy", "Hand and Palmar Spaces", "Nerves of the Upper Limb", "Blood Vessels of Upper Limb", "Joints of Upper Limb"] },
        { "chapter": "Lower Limb", "topics": ["Front of Thigh & Femoral Triangle", "Gluteal Region", "Back of Thigh & Popliteal Fossa", "Leg Anatomy", "Foot and Arches", "Nerves of the Lower Limb", "Blood Vessels of Lower Limb", "Hip, Knee and Ankle Joints"] },
        { "chapter": "Thorax", "topics": ["Thoracic Wall and Intercostal Spaces", "Pleura and Lungs", "Mediastinum", "Heart and Pericardium", "Superior Vena Cava and Aorta", "Trachea and Esophagus"] },
        { "chapter": "Abdomen and Pelvis", "topics": ["Anterior Abdominal Wall", "Inguinal Canal", "Peritoneum", "Stomach and Spleen", "Liver and Extra-hepatic Biliary Apparatus", "Kidneys and Ureters", "Pelvic Viscera", "Perineum"] },
        { "chapter": "Head and Neck", "topics": ["Scalp and Face", "Triangles of the Neck", "Parotid, Submandibular, and Thyroid Glands", "Cranial Cavity and Meninges", "Orbit and Eye Anatomy", "Nasal Cavity", "Pharynx and Larynx"] },
        { "chapter": "Neuroanatomy", "topics": ["Spinal Cord Structure", "Brainstem Anatomy", "Cerebellum", "Cerebrum and Functional Areas", "Ventricles and CSF", "Blood Supply of the Brain", "Cranial Nerves Overview"] }
      ],
      "Biochemistry": [
        { "chapter": "Cell Architecture and Membranes", "topics": ["Biological Membrane Structure", "Membrane Transport Mechanisms", "Intracellular Organelles", "Extracellular Matrix components"] },
        { "chapter": "Carbohydrates", "topics": ["Chemistry of Carbohydrates", "Digestion and Absorption of Carbs", "Glycolysis and Regulation", "TCA Cycle", "Gluconeogenesis", "Glycogen Metabolism", "HMP Shunt Pathway"] },
        { "chapter": "Proteins and Amino Acids", "topics": ["Amino Acid Classification", "Protein Structure Levels", "Digestion and Absorption of Proteins", "Urea Cycle", "Metabolism of Aromatic Amino Acids", "Metabolism of Sulphur containing amino acids", "Specialized products from amino acids"] },
        { "chapter": "Lipids", "topics": ["Chemistry of Lipids", "Digestion and Absorption of Lipids", "Beta Oxidation of Fatty Acids", "Ketone Bodies", "Cholesterol Synthesis", "Lipoproteins (VLDL, LDL, HDL)"] },
        { "chapter": "Enzymes", "topics": ["Enzyme Kinetics", "Enzyme Inhibition", "Isoenzymes", "Clinical Enzymology"] },
        { "chapter": "Vitamins and Minerals", "topics": ["Fat Soluble Vitamins (A, D, E, K)", "Water Soluble Vitamins (B complex and C)", "Calcium and Phosphorus Metabolism", "Iron Metabolism", "Trace Elements"] },
        { "chapter": "Molecular Biology", "topics": ["Structure of DNA and RNA", "DNA Replication", "Transcription", "Translation", "Regulation of Gene Expression", "Recombinant DNA Technology"] }
      ],
      "Physiology": [
        { "chapter": "General Physiology", "topics": ["Homeostasis", "Body Fluid Compartments", "Resting Membrane Potential", "Action Potential"] },
        { "chapter": "Blood", "topics": ["Composition of Blood", "Erythropoiesis", "Hemoglobin and Iron", "Blood Groups and Transfusion", "Hemostasis and Blood Coagulation", "Immunity and WBCs"] },
        { "chapter": "Nerve and Muscle Physiology", "topics": ["Neuron Structure and Function", "Synapse and Neuromuscular Junction", "Skeletal Muscle Contraction", "Smooth Muscle Contraction"] },
        { "chapter": "Digestive System", "topics": ["Salivary Secretion", "Gastric Secretion", "Pancreatic Secretion", "Liver and Biliary Secretion", "Intestinal Motility", "Digestion and Absorption"] },
        { "chapter": "Cardiovascular System", "topics": ["Cardiac Muscle Properties", "Cardiac Cycle", "ECG Overview", "Cardiac Output", "Blood Pressure Regulation", "Coronary Circulation"] },
        { "chapter": "Respiratory System", "topics": ["Mechanics of Breathing", "Lung Volumes and Capacities", "Gas Exchange in Lungs", "Oxygen and Carbon Dioxide Transport", "Regulation of Respiration", "Hypoxia"] },
        { "chapter": "Renal System", "topics": ["Nephron Structure", "Glomerular Filtration Rate (GFR)", "Tubular Reabsorption and Secretion", "Counter Current Mechanism", "Acid-Base Balance", "Micturition"] },
        { "chapter": "Endocrine System", "topics": ["Mechanism of Hormone Action", "Pituitary Gland", "Thyroid Gland", "Parathyroid and Calcium Regulation", "Adrenal Cortex and Medulla", "Endocrine Pancreas"] },
        { "chapter": "Central Nervous System", "topics": ["Sensory Receptors", "Ascending Tracts", "Descending Tracts", "Cerebral Cortex Functions", "Basal Ganglia", "Cerebellum Functions", "Autonomic Nervous System"] },
        { "chapter": "Special Senses", "topics": ["Vision (Optics and Retina)", "Visual Pathway", "Hearing (Cochlea Mechanism)", "Auditory Pathway", "Taste and Smell"] }
      ],
      "Pharmacology": [
        { "chapter": "General Pharmacology", "topics": ["Pharmacokinetics: Absorption and Distribution", "Pharmacokinetics: Metabolism and Excretion", "Pharmacodynamics: Receptor Types", "Drug Interactions", "Adverse Drug Reactions"] },
        { "chapter": "Autonomic Nervous System", "topics": ["Cholinergic Agonists", "Anticholinergic Drugs", "Adrenergic Agonists", "Alpha Blockers", "Beta Blockers"] },
        { "chapter": "Cardiovascular Drugs", "topics": ["Antihypertensive Drugs", "Antianginal Drugs", "Drugs for Heart Failure", "Antiarrhythmic Drugs", "Hypolipidemic Drugs"] },
        { "chapter": "CNS Drugs", "topics": ["General Anesthetics", "Local Anesthetics", "Sedative Hypnotics", "Antiepileptic Drugs", "Antidepressants", "Antipsychotics", "Opioid Analgesics"] },
        { "chapter": "Chemotherapy", "topics": ["Penicillins and Cephalosporins", "Macrolides and Aminoglycosides", "Fluoroquinolones", "Antitubercular Drugs", "Antimalarial Drugs", "Antiviral Drugs", "Anticancer Drugs overview"] }
      ],
      "Pathology": [
         { "chapter": "General Pathology", "topics": ["Cell Injury and Necrosis", "Apoptosis", "Inflammation - Acute", "Inflammation - Chronic", "Tissue Repair and Healing", "Hemodynamic Disorders", "Thrombosis and Embolism", "Neoplasia - Benign vs Malignant", "Carcinogenesis"] },
         { "chapter": "Systemic Pathology", "topics": ["Atherosclerosis", "Ischemic Heart Disease", "Pneumonias", "Tuberculosis Pathology", "Peptic Ulcer Disease", "Cirrhosis of Liver", "Glomerulonephritis", "Breast Carcinoma"] }
      ]
    },
    "BTech": {
      "Data Structures": [
        { "chapter": "Introduction & Arrays", "topics": ["Asymptotic Analysis (Big O)", "1D and 2D Arrays", "Matrix Operations", "Sparse Matrices"] },
        { "chapter": "Linked Lists", "topics": ["Singly Linked Lists", "Doubly Linked Lists", "Circular Linked Lists", "Reversing Linked Lists", "Cycle Detection"] },
        { "chapter": "Stacks & Queues", "topics": ["Stack Implementation", "Infix, Prefix, Postfix Conversions", "Queue Implementation", "Circular Queues", "Priority Queues"] },
        { "chapter": "Trees", "topics": ["Binary Trees", "Tree Traversals (Inorder, Preorder, Postorder)", "Binary Search Trees (BST)", "AVL Trees", "Heaps (Min Heap, Max Heap)"] },
        { "chapter": "Graphs", "topics": ["Graph Representations (Adjacency Matrix/List)", "BFS and DFS Traversals", "Dijkstra's Algorithm", "Kruskal's and Prim's MST", "Topological Sorting"] },
        { "chapter": "Sorting & Searching", "topics": ["Linear and Binary Search", "Bubble, Selection, and Insertion Sort", "Merge Sort", "Quick Sort", "Hashing Techniques"] }
      ],
      "Operating Systems": [
        { "chapter": "Introduction", "topics": ["OS Functions and Architecture", "System Calls", "Process Concept"] },
        { "chapter": "Process Management", "topics": ["Process Scheduling Algorithms (FCFS, SJF, RR)", "Inter-process Communication (IPC)", "Threads and Concurrency"] },
        { "chapter": "Synchronization & Deadlocks", "topics": ["Critical Section Problem", "Semaphores and Mutex", "Producer-Consumer Problem", "Deadlock Characterization", "Banker's Algorithm"] },
        { "chapter": "Memory Management", "topics": ["Paging and Segmentation", "Virtual Memory", "Page Replacement Algorithms (FIFO, LRU)", "Thrashing"] },
        { "chapter": "Storage Management", "topics": ["File System Structure", "Directory Implementation", "Disk Scheduling Algorithms", "RAID Structure"] }
      ],
      "Computer Networks": [
        { "chapter": "Network Basics", "topics": ["OSI and TCP/IP Models", "Network Topologies", "Transmission Media", "Switching Techniques"] },
        { "chapter": "Data Link Layer", "topics": ["Framing", "Error Detection (CRC, Checksum)", "Flow Control (Sliding Window)", "CSMA/CD protocol", "Ethernet"] },
        { "chapter": "Network Layer", "topics": ["IPv4 and IPv6 Addressing", "Subnetting", "Routing Algorithms (Distance Vector, Link State)", "ICMP"] },
        { "chapter": "Transport Layer", "topics": ["TCP Header and Connection Management", "UDP Protocol", "Congestion Control in TCP"] },
        { "chapter": "Application Layer", "topics": ["DNS", "HTTP and HTTPS", "FTP", "SMTP"] }
      ],
      "Database Management Systems": [
        { "chapter": "Introduction to DBMS", "topics": ["File Systems vs DBMS", "Three schema architecture", "Entity-Relationship (ER) Model"] },
        { "chapter": "Relational Model", "topics": ["Relational Algebra", "Relational Calculus", "Key Constraints (Primary, Foreign)"] },
        { "chapter": "SQL", "topics": ["DDL, DML, DCL Commands", "Joins (Inner, Outer, Cross)", "Nested Queries", "Aggregate Functions and Group By"] },
        { "chapter": "Normalization", "topics": ["Functional Dependencies", "1NF, 2NF, 3NF", "Boyce-Codd Normal Form (BCNF)", "Lossless Join Decomposition"] },
        { "chapter": "Transactions", "topics": ["ACID Properties", "Serializability", "Concurrency Control (Locking Protocols)", "Deadlock Handling", "Database Recovery Techniques"] }
      ],
      "Object Oriented Programming": [
        { "chapter": "OOP Principles", "topics": ["Classes and Objects", "Encapsulation and Data Hiding", "Inheritance types", "Polymorphism (Compile time and Run time)"] },
        { "chapter": "Advanced Concepts", "topics": ["Constructors and Destructors", "Abstract Classes and Interfaces", "Exception Handling", "File Handling", "Multithreading Basics"] }
      ],
      "Design and Analysis of Algorithms": [
        { "chapter": "Algorithm Foundations", "topics": ["Time and Space Complexity", "Master Theorem", "Recurrence Relations"] },
        { "chapter": "Divide and Conquer", "topics": ["Merge Sort Analysis", "Quick Sort Analysis", "Strassen’s Matrix Multiplication"] },
        { "chapter": "Greedy Algorithms", "topics": ["Fractional Knapsack", "Huffman Coding", "Activity Selection Problem"] },
        { "chapter": "Dynamic Programming", "topics": ["0/1 Knapsack Problem", "Longest Common Subsequence", "Matrix Chain Multiplication", "Bellman-Ford Algorithm"] }
      ]
    }
  }
};

fs.writeFileSync('d:\\notebook lm\\data\\syllabus_extraction.json', JSON.stringify(syllabusData, null, 2));
console.log("Massive Comprehensive Syllabus JSON generated successfully!");
