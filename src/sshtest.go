package main

import (
	"os"
	"log"
	"golang.org/x/crypto/ssh"
	"golang.org/x/crypto/ssh/knownhosts"
	"path/filepath"
	"bufio"
	"io"
	"fmt"
	//"strconv"
	"net"
	"errors"
	"syscall"
)

type SSH struct {
	host string
	port int
	key_filename string
	password string
}

func check(e error) {
	if e != nil {
		log.Fatal(e)
	}
}

func readSize(file *os.File) int64 {
	stat, err := file.Stat()
	check(err)
	return stat.Size()
}

func readFile(filename string) []byte {
	file, err := os.Open(filename)
	check(err)
	defer file.Close()
	// Read the file into a byte slice
	bs := make([]byte, readSize(file))
	_, err = bufio.NewReader(file).Read(bs)
	if err != nil && err != io.EOF {
		fmt.Println(err)
	}
	return bs
}

func sshConnectWithPKey(hostname string, port string, user string, pKeyFileName string) (*ssh.Client, *ssh.Session, error) {
	hostString := net.JoinHostPort(hostname, port)
	pKey := readFile(pKeyFileName)
	signer, err := ssh.ParsePrivateKey(pKey)
	check(err)

	//hostKeyCallback, err := knownhosts.New(knownHostsFile)
	//check(err)

	conf := &ssh.ClientConfig{
		User: user,
		Auth: []ssh.AuthMethod{
			ssh.PublicKeys(signer),
		},
	}

	conf.HostKeyCallback = ssh.InsecureIgnoreHostKey()

	// var conn *ssh.Client
	// fmt.Println("Connecting.")
	// conn, err = ssh.Dial("tcp", hostString, conf)
	// sshCheck(err)
	// //defer conn.Close()
	// fmt.Println("Connected.")

	// var session *ssh.Session
	// session, err = conn.NewSession()
	// check(err)
	//defer session.Close()

	client, err := ssh.Dial("tcp", hostString, conf)
	if err != nil {
		return nil, nil, err
	}

	session, err := client.NewSession()
	if err != nil {
		return nil, nil, err
	}

	return client, session, nil

	return true
}

func tryConnectWithPrivateKey(host string, port string, user string, pKeyPath string) bool {
	client, session, err := sshConnectWithPKey(host, port, user, pKeyPath)
	command := "ls -l /"
	output, err := session.CombinedOutput(command)
	return true
}

func sshCheck(err error) {
	if err != nil {
		if errors.Is(err, syscall.ECONNREFUSED) {
			fmt.Println("Connection refused.  CAUGHT IT.")
		}
	}
}

func main() {
	homedir, err := os.UserHomeDir()
	check(err)

	sshdir := filepath.Join(homedir, ".ssh")

	user := "art"
	host := "192.168.1.198"
	port := "22"

	pKeyPath := filepath.Join(sshdir, "id_rsa_legion")

	success := tryConnectWithPrivateKey(
		host,
		port,
		user,
		pKeyPath,
	)
	if success {
		fmt.Println("Successful.")
	} else {
		fmt.Println("Failure.")
	}
}

