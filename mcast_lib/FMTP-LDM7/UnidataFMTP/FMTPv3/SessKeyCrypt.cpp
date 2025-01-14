/**
 * Session key cryptography.
 *
 *        File: PubKeyCrypt.cpp
 *  Created on: Sep 2, 2020
 *      Author: Steven R. Emmerson
 */

#include "SslHelp.h"
#include "SessKeyCrypt.h"

#include <openssl/pem.h>
#include <openssl/err.h>
#include <openssl/hmac.h>
#include <openssl/evp.h>
#include <openssl/crypto.h>
#include <openssl/rand.h>

#include <exception>
#include <system_error>

SessKeyCrypt::SessKeyCrypt()
	: rsa{nullptr}
{}

SessKeyCrypt::~SessKeyCrypt()
{
	::RSA_free(rsa);
}

Decryptor::Decryptor()
	: SessKeyCrypt{}
	, pubKey{}
{
    BIGNUM* bigNum = ::BN_new();
    if (bigNum == nullptr)
        throw std::runtime_error("BN_new() failure. "
                "Code=" + std::to_string(ERR_get_error()));

    try {
        if (::BN_set_word(bigNum, RSA_F4) == 0)
            throw std::runtime_error("BN_set_word() failure. "
                    "Code=" + std::to_string(ERR_get_error()));

        rsa = ::RSA_new();
        if (rsa == nullptr)
            throw std::runtime_error("RSA_new() failure. "
                    "Code=" + std::to_string(ERR_get_error()));

        try {
            const int numBits = 2048;

            SslHelp::initRand(numBits/8);
            if (::RSA_generate_key_ex(rsa, numBits, bigNum, NULL) == 0)
                throw std::runtime_error("RSA_generate_key_ex() failure. "
                        "Code=" + std::to_string(ERR_get_error()));

            BIO* bio = ::BIO_new(BIO_s_mem());
            if (bio == nullptr)
                throw std::runtime_error("BIO_new() failure. "
                        "Code=" + std::to_string(ERR_get_error()));

            try {
                // Doesn't NUL-terminate
                if (::PEM_write_bio_RSAPublicKey(bio, rsa) == 0)
                    throw std::runtime_error("PEM_write_bio_RSAPublicKey() "
                            "failure. "
                            "Code=" + std::to_string(ERR_get_error()));

                const size_t keyLen = BIO_pending(bio);
                char         keyBuf[keyLen]; // NB: No trailing NUL

                if (::BIO_read(bio, keyBuf, keyLen) != keyLen)
                    throw std::runtime_error("BIO_read() failure. "
                            "Code=" + std::to_string(ERR_get_error()));

                // Finally!
                pubKey = std::string{static_cast<char*>(keyBuf), keyLen};

                ::BIO_free_all(bio);
            } // `bio` allocated
            catch (const std::exception& ex) {
                ::BIO_free_all(bio);
                throw;
            }
        } // `rsa` allocated
        catch (const std::exception& ex) {
            ::RSA_free(rsa);
            throw;
        }

        ::BN_free(bigNum);
    } // `bigNum` allocated
    catch (const std::exception& ex) {
        ::BN_free(bigNum);
        throw;
    }
}

const std::string& Decryptor::getPubKey() const noexcept
{
	return pubKey;
}

std::string Decryptor::decrypt(const std::string& cipherText) const
{
	char      sessKey[RSA_size(rsa)];
	const int keyLen = ::RSA_private_decrypt(RSA_size(rsa),
			reinterpret_cast<const unsigned char*>(cipherText.data()),
			reinterpret_cast<unsigned char*>(sessKey), rsa, padding);
	if (keyLen == -1)
		throw std::runtime_error("RSA_private_decrypt() failure. "
				"Code=" + std::to_string(ERR_get_error()));

	return std::string(sessKey, keyLen);
}

/******************************************************************************/

Encryptor::Encryptor(const std::string& pubKey)
	: SessKeyCrypt{}
{
	BIO* bio = BIO_new_mem_buf(pubKey.data(), pubKey.size());
	if (bio == nullptr)
		throw std::runtime_error("BIO_new_mem_buf() failure. "
				"Code=" + std::to_string(ERR_get_error()));

	try {
		rsa = PEM_read_bio_RSAPublicKey(bio, nullptr, nullptr, nullptr);
		if (rsa == nullptr)
			throw std::runtime_error("PEM_read_bio_RSAPublicKey() failure. "
					"Code=" + std::to_string(ERR_get_error()));

		BIO_free_all(bio);
	} // `bio` allocated
	catch (const std::exception& ex) {
		BIO_free_all(bio);
		throw;
	}
}

std::string Encryptor::encrypt(const std::string& sessKey) const
{
	char       cipherText[RSA_size(rsa)];
	const auto cipherLen = RSA_public_encrypt(sessKey.size(),
			reinterpret_cast<const unsigned char*>(sessKey.data()),
			reinterpret_cast<unsigned char*>(cipherText), rsa, padding);
	if (cipherLen == -1)
		throw std::runtime_error("(RSA_public_encrypt) failure. "
				"Code=" + std::to_string(ERR_get_error()));

	return std::string(cipherText, cipherLen);
}
