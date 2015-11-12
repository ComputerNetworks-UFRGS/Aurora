# Inspired in virtinst module
import libvirt


def auth_cb(creds, (passwordcb, passwordcreds)):
    print "Creds: ", creds
    print "Passwordcb: ", passwordcb
    print "Passwordcreds: ", passwordcreds

    for cred in creds:
        if cred[0] not in passwordcreds:
            raise RuntimeError("Unknown cred type '%s', expected only "
                               "%s" % (cred[0], passwordcreds))


    return passwordcb(creds)


def password_cb(creds):
    retindex = 4

    for cred in creds:
        credtype, prompt, ignore, ignore, ignore = cred
        prompt += ": "

        res = cred[retindex]
        if credtype == libvirt.VIR_CRED_AUTHNAME:
            #res = raw_input(prompt)
            res = "aurora"
        elif credtype == libvirt.VIR_CRED_PASSPHRASE:
            #import getpass
            #res = getpass.getpass(prompt)
            res = "q1w2e3r4t5"
        else:
            raise RuntimeError("Unknown auth type in creds callback: %d" %
                               credtype)

        cred[retindex] = res
    return 0


def open(uri, passwordcb):
    valid_auth_options = [libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE]
    authcb = auth_cb
    authcb_data = passwordcb

    conn = libvirt.openAuth(uri, [valid_auth_options, auth_cb, (authcb_data, valid_auth_options)], 0)

    return conn

if __name__ == "__main__":
    conn = open("qemu+tcp://auroravm/system", password_cb)

    print "Done", conn.getInfo()
