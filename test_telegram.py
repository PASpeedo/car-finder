import unittest
from collector.telegram_notify import chat_fingerprint, protect_chat, recover_chat

class PersistedChatTests(unittest.TestCase):
    def test_round_trip(self):
        token="testing-secret-token"
        chat="1234567890"
        state={"chat_fingerprint":chat_fingerprint(token,chat),
               "chat_cipher_hex":protect_chat(token,chat)}
        self.assertEqual(recover_chat(token,state),chat)
        self.assertNotIn(chat,state["chat_cipher_hex"])
    def test_negative_chat_id(self):
        token="test-token"
        chat="-1001234567890"
        state={"chat_fingerprint":chat_fingerprint(token,chat),
               "chat_cipher_hex":protect_chat(token,chat)}
        self.assertEqual(recover_chat(token,state),chat)
    def test_wrong_token_and_tampering(self):
        token="test-token"
        chat="987654321"
        cipher=protect_chat(token,chat)
        state={"chat_fingerprint":chat_fingerprint(token,chat),
               "chat_cipher_hex":cipher}
        self.assertIsNone(recover_chat("different-token",state))
        state["chat_cipher_hex"]=cipher[:-2]+("00" if cipher[-2:]!="00" else "01")
        self.assertIsNone(recover_chat(token,state))
    def test_each_encryption_uses_fresh_nonce(self):
        token="test-token"
        self.assertNotEqual(protect_chat(token,"123456"),protect_chat(token,"123456"))
if __name__=="__main__":unittest.main()
