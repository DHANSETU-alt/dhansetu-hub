import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import voice


class TestResolveVoice(unittest.TestCase):
    def test_explicit_voice_name_wins(self):
        self.assertEqual(voice.resolve_voice(voice="Moira", gender="female"), "Moira")

    def test_gender_female_maps_to_samantha(self):
        self.assertEqual(voice.resolve_voice(gender="female"), voice.VOICE_FEMALE)

    def test_gender_male_maps_to_daniel(self):
        self.assertEqual(voice.resolve_voice(gender="male"), voice.VOICE_MALE)

    def test_no_args_defaults_to_male(self):
        self.assertEqual(voice.resolve_voice(), voice.VOICE_MALE)

    def test_unrecognized_gender_falls_back_to_male(self):
        self.assertEqual(voice.resolve_voice(gender="robot"), voice.VOICE_MALE)

    def test_gender_is_case_insensitive(self):
        self.assertEqual(voice.resolve_voice(gender="FEMALE"), voice.VOICE_FEMALE)


class TestSpeak(unittest.TestCase):
    @patch("orchestrator.voice.subprocess.run")
    @patch("orchestrator.voice.shutil.which", side_effect=lambda name: "/usr/bin/say" if name == "say" else None)
    def test_speak_invokes_say_with_resolved_voice(self, _mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        ok = voice.speak("Good evening.", gender="female")
        self.assertTrue(ok)
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0], ["say", "-v", voice.VOICE_FEMALE, "Good evening."])

    @patch("orchestrator.voice.subprocess.run")
    @patch("orchestrator.voice.shutil.which", side_effect=lambda name: "/usr/bin/say" if name == "say" else None)
    def test_speak_explicit_voice_overrides_gender(self, _mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        voice.speak("Hi.", voice="Karen", gender="male")
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0][2], "Karen")

    @patch("orchestrator.voice.shutil.which", return_value=None)
    def test_speak_returns_false_when_say_missing(self, _mock_which):
        self.assertFalse(voice.speak("Hi."))

    @patch("orchestrator.voice.subprocess.run")
    @patch("orchestrator.voice.shutil.which", side_effect=lambda name: "/usr/bin/espeak-ng" if name == "espeak-ng" else None)
    def test_speak_uses_gujarati_linux_voice(self, _mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.assertTrue(voice.speak("સિસ્ટમ તૈયાર છે", gender="female", language="gu"))
        self.assertEqual(mock_run.call_args.args[0][:5], ["/usr/bin/espeak-ng", "-v", "gu+f3", "-s", "165"])


class TestContainsWakeWord(unittest.TestCase):
    def test_detects_exact_wake_word(self):
        self.assertTrue(voice._contains_wake_word("Shakthi check my finance report"))

    def test_detects_mishearing_variant(self):
        self.assertTrue(voice._contains_wake_word("Shout-T check my finance report"))

    def test_rejects_unrelated_speech(self):
        self.assertFalse(voice._contains_wake_word("what's for dinner tonight"))

    def test_empty_string_is_false(self):
        self.assertFalse(voice._contains_wake_word(""))


class TestTranscribeAndExecuteReusesTranscription(unittest.TestCase):
    @patch("orchestrator.voice.db.get_conn")
    @patch("orchestrator.voice.db.log_voice_command")
    @patch("orchestrator.voice.speak")
    @patch("orchestrator.voice.access.identify", return_value="owner")
    @patch("orchestrator.voice.transcribe")
    def test_precomputed_transcription_skips_second_stt_call(
        self, mock_transcribe, mock_identify, mock_speak, mock_log, mock_get_conn
    ):
        mock_get_conn.return_value.__enter__.return_value = MagicMock()
        precomputed = {"text": "Shakthi check bugs", "language": "en", "confidence": 0.9}
        result = voice._transcribe_and_execute(
            audio=object(), identity_passphrase=None, transcription=precomputed
        )
        mock_transcribe.assert_not_called()
        self.assertEqual(result["transcript"], "Shakthi check bugs")

    @patch("orchestrator.voice.db.get_conn")
    @patch("orchestrator.voice.db.log_voice_command")
    @patch("orchestrator.voice.speak")
    @patch("orchestrator.voice.access.identify", return_value="owner")
    @patch("orchestrator.voice.transcribe")
    def test_missing_transcription_falls_back_to_real_stt_call(
        self, mock_transcribe, mock_identify, mock_speak, mock_log, mock_get_conn
    ):
        mock_get_conn.return_value.__enter__.return_value = MagicMock()
        mock_transcribe.return_value = {"text": "Shakthi check bugs", "language": "en", "confidence": 0.9}
        voice._transcribe_and_execute(audio=object(), identity_passphrase=None)
        mock_transcribe.assert_called_once()

    @patch("orchestrator.voice.db.get_conn")
    @patch("orchestrator.voice.db.log_voice_command")
    @patch("orchestrator.voice.speak")
    @patch("orchestrator.voice.access.identify", return_value="owner")
    @patch("orchestrator.voice.transcribe")
    def test_speak_response_passes_through_gender(
        self, mock_transcribe, mock_identify, mock_speak, mock_log, mock_get_conn
    ):
        mock_get_conn.return_value.__enter__.return_value = MagicMock()
        precomputed = {"text": "Shakthi check bugs", "language": "en", "confidence": 0.9}
        voice._transcribe_and_execute(
            audio=object(), identity_passphrase=None, transcription=precomputed, gender="female"
        )
        mock_speak.assert_called_once()
        _, kwargs = mock_speak.call_args
        self.assertEqual(kwargs.get("gender"), "female")


if __name__ == "__main__":
    unittest.main()
