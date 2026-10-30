<!-- machine translation of README.md; the English README is the complete copy -->
# Maintainability Agent

[English](README.md) | [Español](README.es.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | **हिन्दी** | [简体中文](README.zh-CN.md)

> मशीन अनुवाद। [अंग्रेज़ी README](README.md) ही पूर्ण और नियमित रूप से अद्यतन संस्करण है।

## यह क्या है

एक नियतात्मक (deterministic), ऑफ़लाइन मेंटेनेबिलिटी ऑडिट, जिसका परिणाम किसी AI
कोडिंग एजेंट के लिए एक **सीमित कार्य-आदेश** होता है: हर निष्कर्ष के लिए एक
कॉपी-पेस्ट करने योग्य प्रॉम्प्ट, जो कहता है *ठीक यही सुधारो और कुछ और रीफ़ैक्टर मत
करो*। यह किसी भाषा मॉडल का उपयोग नहीं करता और आपका कोड किसी सेवा को नहीं भेजता।
ग्रेड परिपक्व ओपन-सोर्स रिपॉज़िटरी पर कैलिब्रेट किए गए हैं।

मुख्य इंटरफ़ेस चैट है (आपके AI सहायक के लिए एक स्थानीय MCP सर्वर); CLI, CI और
स्क्रिप्ट के लिए है।

## इंस्टॉल करें

```bash
pip install maintainability-agent
```

## पहली बार चलाएँ

```bash
maintainability-agent --root . --output maintainability-report.md
```

चैट/MCP सेटअप, केवल-बदलाव मोड, बेसलाइन और CI एकीकरण का विवरण
[अंग्रेज़ी README](README.md) में है।

## लाइसेंस

MIT.
